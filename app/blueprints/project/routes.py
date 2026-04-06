"""
routes.py — Project blueprint routes.

Routes:
  GET/POST /project/import-project/proj-<proj_id>/item-<item_id>
"""

import ast
import re
from datetime import datetime

import pandas as pd
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.blueprints.project import bp
from app.extensions import db
from app.models.master import (
    companyMaster,
    addressMaster,
    engineerMaster,
    industryMaster,
    regionMaster,
)
from app.models.transactional import (
    itemMaster,
    projectMaster,
    itemRevisionTable,
    valveDetailsMaster,
    caseMaster,
    actuatorMaster,
    actuatorCaseData,
    rotaryCaseData,
    volumeTank,
    accessoriesData,
    itemNotesData,
    caseWarnings,
    valveDataWarnings,
    addressProject,
    engineerProject,
)
from app.blueprints.project.helpers_import import (
    get_by_id,
    get_by_name,
    get_null_or_value,
    safe_get_id,
    getCheckedValue,
    getCheckedElement,
    int_to_float_convertor,
    clean_item_data,
    map_valve_fk,
    map_actuator_fk,
    testcase_module,
)
from app.blueprints.project.helpers import generate_quote


@bp.route('/import-project/proj-<int:proj_id>/item-<int:item_id>', methods=['POST'])
@login_required
def import_project(item_id, proj_id):
    item = get_by_id(itemMaster, item_id)

    if request.method == 'POST':
        # --- quote number ---
        if current_user.fccUser and current_user.projType == 1:
            quote_no = request.form.get('quote_no', '').strip()
            if not re.fullmatch(r'Q\d{7}', quote_no):
                flash("Quote format should be 'Q' followed by 7 digit Number", 'failure')
                return render_template(
                    'project/import_project.html',
                    item=item, page='importProject', user=current_user,
                )
        elif current_user.fccUser and current_user.projType == 2:
            quote_no = generate_quote('T')
        else:
            quote_no = generate_quote('C')

        file = request.files.get('file')
        df = pd.read_excel(file, header=None, keep_default_na=False)

        # Testcase users get a simpler import path
        if current_user.projType == 2:
            testcase_module(item_id, proj_id, quote_no)
            return redirect(url_for('home.home', item_id=item_id, proj_id=proj_id))

        # ---- parse section indices ----
        def _find_index(marker: str) -> int:
            return df[df.apply(
                lambda row: row.astype(str).str.contains(marker).any(), axis=1
            )].index[0]

        items_index        = _find_index('Items')
        valveWarnings_index = _find_index('ValveWarnings')
        case_index         = _find_index('CaseDetails')
        caseWarnings_index = _find_index('CaseWarnings')
        actuator_index     = _find_index('Actuator')
        volumetank_index   = _find_index('VolumeTank')
        accessories_index  = _find_index('Accessories')
        itemnotes_index    = _find_index('ItemNotes')
        customer_index     = _find_index('Customer')
        end_index          = _find_index('FinishExcel')

        # ---- parse project row ----
        proj_row    = df.iloc[2]
        proj_headers = df.iloc[1].to_list()
        proj_data    = df.iloc[2].to_list()

        _skip_proj = {'id', 'projectId', '', 'bidDueDate', 'receiptDate',
                      'enquiryReceivedDate', 'cur_revno', 'revisionNo'}
        project_details = {
            k: [v] for k, v in zip(proj_headers, proj_data) if k not in _skip_proj
        }

        # ---- parse customer ----
        cus_headers = df.iloc[customer_index + 1].to_list()
        cus_values  = df.iloc[customer_index + 2].to_list()
        cus_details = {
            k: get_null_or_value(v)
            for k, v in zip(cus_headers, cus_values)
            if k not in {'id', ''}
        }
        company_name    = [cus_details['Companyname'],  cus_details['Enduser']]
        company_address = [cus_details['Companyaddress'], cus_details['EnduserAdd']]
        engg_names      = [cus_details['AppEngg'],       cus_details['ContactEngg']]

        # ---- parse items ----
        item_headers = df.iloc[items_index + 1].to_list()
        _skip_item = {'id', '', 'fluidPropertiesId', 'nde1Id', 'nde2Id', 'cur_revno'}
        all_items = [
            {k: [v] for k, v in zip(item_headers, df.iloc[r].to_list()) if k not in _skip_item}
            for r in range(items_index + 2, case_index - 1)
        ]

        # ---- parse valve warnings ----
        vw_headers = df.iloc[valveWarnings_index + 1].to_list()
        vw_start   = valveWarnings_index + 2
        vw_end     = end_index - 1
        all_valve_warnings = []
        if vw_start != vw_end:
            all_valve_warnings = [
                {k: [v] for k, v in zip(vw_headers, df.iloc[r]) if k not in {'id', ''}}
                for r in range(vw_start, vw_end)
            ]

        # ---- parse cases ----
        case_headers = df.iloc[case_index + 1].to_list()
        cs_start = case_index + 2; cs_end = actuator_index - 1
        all_item_cases = []
        if cs_start != cs_end:
            all_item_cases = [
                {k: v for k, v in zip(case_headers, df.iloc[r]) if k not in {'id', ''}}
                for r in range(cs_start, cs_end)
            ]

        # ---- parse case warnings ----
        warn_headers  = df.iloc[caseWarnings_index + 1].to_list()
        cw_start = caseWarnings_index + 2; cw_end = valveWarnings_index - 1
        all_case_warnings = []
        if cw_start != cw_end:
            all_case_warnings = [
                {k: v for k, v in zip(warn_headers, df.iloc[r]) if k not in {'id', ''}}
                for r in range(cw_start, cw_end)
            ]

        # ---- parse actuators ----
        act_headers = df.iloc[actuator_index + 1].to_list()
        _skip_act   = {'id', '', 'slidingActuatorId', 'actuatorMasterId', 'rotaryActuatorId'}
        act_start = actuator_index + 2; act_end = accessories_index - 1
        act_list = []
        all_actuators = []
        if act_start != act_end:
            act_list = [df.iloc[r] for r in range(act_start, act_end)]
            all_actuators = [
                {k: [v] for k, v in zip(act_headers, row) if k not in _skip_act}
                for row in act_list
            ]

        # ---- parse accessories ----
        acc_headers = df.iloc[accessories_index + 1].to_list()
        acc_start = accessories_index + 2; acc_end = volumetank_index - 1
        acc_list = []
        all_accessories = []
        if acc_start != acc_end:
            acc_list = [df.iloc[r] for r in range(acc_start, acc_end)]
            all_accessories = [
                {k: [v] for k, v in zip(acc_headers, row) if k not in {'id', ''}}
                for row in acc_list
            ]

        # ---- parse volume tanks ----
        vt_headers = df.iloc[volumetank_index + 1].to_list()
        vt_start = volumetank_index + 2; vt_end = itemnotes_index - 1
        all_volumetank = []
        if vt_start != vt_end:
            all_volumetank = [
                {k: v for k, v in zip(vt_headers, df.iloc[r]) if k not in {'id', ''}}
                for r in range(vt_start, vt_end)
            ]

        # ---- parse item notes ----
        notes_headers = df.iloc[itemnotes_index + 1].to_list()
        note_start = itemnotes_index + 2; note_end = customer_index - 1
        all_itemnotes = []
        if note_start != note_end:
            all_itemnotes = [
                {k: [v] for k, v in zip(notes_headers, df.iloc[r]) if k not in {'id', ''}}
                for r in range(note_start, note_end)
            ]

        # ------------------------------------------------------------------ #
        # Persist project
        # ------------------------------------------------------------------ #
        new_project = projectMaster(
            user=current_user,
            projectRef='TBA',
            enquiryRef='TBA',
            isFccProject=current_user.fccUser,
        )
        try:
            new_project.quoteNo = quote_no
            db.session.add(new_project)
            db.session.commit()
        except IntegrityError as exc:
            import traceback
            print('---------------------')
            traceback.print_exc()
            db.session.rollback()
            if 'unique' in str(exc.orig).lower() or 'duplicate' in str(exc.orig).lower():
                flash('Quote Number already exists!', 'failure')
            else:
                flash('Database error occurred. Please try again.', 'failure')
            return render_template(
                'project/import_project.html',
                item=item, page='importProject', user=current_user,
            )

        time = datetime.now()
        project_details['IndustryId'] = [get_by_name(industryMaster, project_details['IndustryId'][0])]
        project_details['regionID']   = [get_by_name(regionMaster,   project_details['regionID'][0])]
        project_details['industry']   = project_details.pop('IndustryId')
        project_details['region']     = project_details.pop('regionID')

        for key in project_details:
            project_details[key] = get_null_or_value(project_details[key])

        new_project.revision            = 0
        new_project.cur_revno           = 0
        new_project.enquiryReceivedDate = time
        new_project.receiptDate         = time
        new_project.bidDueDate          = time
        new_project.industry            = project_details['industry'][0]
        new_project.region              = project_details['region'][0]
        new_project.trim_exit_velocity  = 'yes'
        db.session.commit()

        # ---- customers / addresses / engineers ----
        for idx, (cname, caddr, engg) in enumerate(
            zip(company_name, company_address, engg_names)
        ):
            company = db.session.query(companyMaster).filter_by(name=cname).first()
            if not company:
                company = companyMaster(name=cname)
                db.session.add(company)
                db.session.commit()

            if current_user.fccUser:
                address = db.session.query(addressMaster).filter_by(
                    address=caddr, companyId=company.id).first()
            else:
                address = db.session.query(addressMaster).filter_by(
                    address=caddr, companyId=company.id, user=current_user).first()

            if not address:
                address = addressMaster(
                    address=caddr, company=company,
                    user=current_user, isActive=True,
                )
                db.session.add(address)
                db.session.commit()

            db.session.add(addressProject(
                address=address, project=new_project, isCompany=(idx == 0),
            ))
            db.session.commit()

            engineer = db.session.query(engineerMaster).filter_by(name=engg).first()
            if not engineer:
                engineer = engineerMaster(name=engg, designation='Engineer')
                db.session.add(engineer)
                db.session.commit()

            db.session.add(engineerProject(
                project=new_project, engineer=engineer, isApplication=(idx == 0),
            ))
            db.session.commit()

        # ---- items ----
        item_element_dict = {}
        val_ele = {}
        item_num = 1
        valve_num = 1

        for item_ in all_items:
            new_item = itemMaster(project=new_project)
            db.session.add(new_item)
            db.session.commit()

            for key in item_:
                item_[key] = get_null_or_value(item_[key])

            new_item.update(item_, new_item.id)
            item_element_dict[item_num] = new_item

            new_item.revision      = 0
            new_item.itemNumber    = item_num
            new_item.draft_status  = -1
            new_item.initial_status = 1
            new_item.cur_revType   = 'initial'
            new_item.cur_status    = 'In progress'
            new_item.cur_revno     = 0
            db.session.commit()
            item_num += 1

            if not acc_list:
                db.session.add(accessoriesData(item=new_item, revision=0, draft_status=-1))
                db.session.commit()

            if not act_list:
                db.session.add(actuatorMaster(item=new_item, revision=0, draft_status=-1))
                db.session.commit()

            db.session.add(itemRevisionTable(
                item=new_item,
                itemRevisionNo=0,
                status='In progress',
                prepared_by=current_user.code,
                time=datetime.today().strftime('%Y-%m-%d %H:%M'),
            ))
            db.session.commit()

            # valve details
            new_valve = valveDetailsMaster(item=new_item)
            db.session.add(new_valve)
            db.session.commit()

            item_ = clean_item_data(item_)
            item_['isActive'] = [1]
            item_['solveCase'] = [1]
            if item_['minTemp'] == (None,):
                item_['minTemp'] = (0,)

            item_ = map_valve_fk(item_)
            new_valve.update(item_, new_valve.id)
            new_valve.revision      = 0
            new_valve.draft_status  = -1
            new_valve.fluidproperties = None
            new_valve.nde1__        = None
            new_valve.nde2__        = None
            db.session.commit()

            val_ele[valve_num] = new_valve
            valve_num += 1

        # ---- valve warnings ----
        for vwar in all_valve_warnings:
            val_element = val_ele[vwar['valveWarningId'][0]]
            for key in vwar:
                vwar[key] = get_null_or_value(vwar[key])

            new_vw = valveDataWarnings(valve_warning=val_element)
            db.session.add(new_vw)
            db.session.commit()

            vw_obj = db.session.get(valveDataWarnings, new_vw.id)
            del vwar['valveWarningId']
            vw_obj.update(vwar, vw_obj.id)

        # ---- cases ----
        case_element = {}
        case_num = 1
        _case_kv = {'flowrate', 'inletPressure', 'outletPressure', 'inletTemp',
                    'specificHeatRatio', 'specificGravity', 'molecularWeight',
                    'kinematicViscosity'}

        for case_ in all_item_cases:
            item_element = item_element_dict[case_['itemId']]
            case_['revision'] = -1

            for key in case_:
                case_[key] = getCheckedValue(case_[key])
                case_[key] = int_to_float_convertor(case_[key])
                if key in _case_kv and case_[key] is None:
                    case_[key] = 0

            new_case = caseMaster(item=item_element)
            db.session.add(new_case)
            db.session.commit()

            if case_['cv_lists'] is not None:
                case_['cv_lists'] = [float(x.strip()) for x in case_['cv_lists'].split(',')]

            del case_['itemId']
            case_obj = db.session.get(caseMaster, new_case.id)
            case_obj.update(case_, case_obj.id)
            case_obj.revision     = 0
            case_obj.draft_status = -1
            db.session.commit()

            case_element[case_num] = new_case
            case_num += 1

        # ---- case warnings ----
        for war_ in all_case_warnings:
            case_ele = case_element[war_['caseId']]
            for key in war_:
                war_[key] = get_null_or_value(war_[key])

            new_cw = caseWarnings(case=case_ele)
            db.session.add(new_cw)
            db.session.commit()

            cw_obj = db.session.get(caseWarnings, new_cw.id)
            del war_['caseId']
            cw_obj.update(war_, cw_obj.id)

        # ---- actuators ----
        act_element_dict = {}
        act_count = 1

        for act_ in all_actuators:
            item_element = item_element_dict[act_['itemId'][0]]
            del act_['itemId']

            new_act = actuatorMaster(item=item_element, revision=0, draft_status=-1)
            db.session.add(new_act)
            db.session.commit()
            act_element_dict[act_count] = new_act
            act_count += 1

            act_['revision']     = [0]
            act_['draft_status'] = [-1]
            for key in act_:
                act_[key] = get_null_or_value(act_[key])

            act_obj = db.session.get(actuatorMaster, new_act.id)
            act_obj.update(act_, act_obj.id)

            if new_act.actSelectionType == 'sliding':
                new_act_case = actuatorCaseData(
                    actuator_=new_act, revision=0, draft_status=-1,
                )
                db.session.add(new_act_case)
                db.session.commit()

                act_ = map_actuator_fk(act_)
                act_case_obj = db.session.get(actuatorCaseData, new_act_case.id)
                act_case_obj.update(act_, act_case_obj.id)
                act_case_obj.revision     = 0
                act_case_obj.draft_status = -1
                db.session.commit()

            elif new_act.actSelectionType == 'rotary':
                new_rot_case = rotaryCaseData(
                    actuator_=new_act, revision=0, draft_status=-1,
                )
                db.session.add(new_rot_case)
                db.session.commit()

                rot_obj = db.session.get(rotaryCaseData, new_rot_case.id)
                rot_obj.update(act_, rot_obj.id)
                rot_obj.revision     = 0
                rot_obj.draft_status = -1
                db.session.commit()

        # ---- volume tanks ----
        for vt_ in all_volumetank:
            act_element = act_element_dict[vt_['actuatorMasterId']]

            new_vt = volumeTank(actuator_=act_element)
            db.session.add(new_vt)
            db.session.commit()

            vt_obj = db.session.get(volumeTank, new_vt.id)
            for key in vt_:
                vt_[key] = getCheckedValue(vt_[key])

            del vt_['actuatorMasterId']
            if vt_.get('end_of_strokes') not in ('', 'N/A', None):
                vt_['end_of_strokes'] = ast.literal_eval(vt_['end_of_strokes'])
            vt_['revision'] = 0
            vt_obj.update(vt_, vt_obj.id)
            db.session.commit()

        # ---- accessories ----
        for acc_ in all_accessories:
            item_element = item_element_dict[acc_['itemId'][0]]
            new_acc = accessoriesData(item=item_element, revision=0, draft_status=-1)
            db.session.add(new_acc)
            db.session.commit()

            acc_obj = db.session.get(accessoriesData, new_acc.id)
            for key in acc_:
                acc_[key] = get_null_or_value(acc_[key])
            del acc_['itemId']
            acc_['revision']     = [0]
            acc_['draft_status'] = [-1]
            acc_obj.update(acc_, acc_obj.id)
            db.session.commit()

        # ---- item notes ----
        for note_ in all_itemnotes:
            item_element = item_element_dict[note_['itemId'][0]]
            new_note = itemNotesData(item=item_element, revision=0, draft_status=-1)
            db.session.add(new_note)
            db.session.commit()

            note_obj = db.session.get(itemNotesData, new_note.id)
            for key in note_:
                note_[key] = get_null_or_value(note_[key])
            del note_['itemId']
            note_['revision']     = [0]
            note_['draft_status'] = [-1]
            note_obj.update(note_, note_obj.id)
            db.session.commit()

        flash('Project imported successfully', 'success')
        return redirect(url_for('home.home', item_id=item_id, proj_id=proj_id))

    # return render_template(
    #     'project/import_project.html',
    #     item=item, page='importProject', user=current_user,
    # )
