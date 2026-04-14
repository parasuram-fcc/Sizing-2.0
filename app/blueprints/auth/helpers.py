"""
app/blueprints/auth/helpers.py

Helper functions for auth routes.
Extracted from routes.py to keep route functions thin.
No business logic has been changed.
"""
import random
import logging
from datetime import datetime

from flask_mail import Message

from app.extensions import db, mail

log = logging.getLogger(__name__)
from app.models import (
    OTP, engineerMaster, projectMaster, itemMaster,
    valveDetailsMaster, actuatorMaster, accessoriesData,
    companyMaster, addressMaster, addressProject, fluidState,
)


def send_otp(username):
    """Generate a 6-digit OTP, persist it, and email it to `username`.

    Returns True if the email was sent successfully, False otherwise.
    Reuses an existing OTP row if one already exists for the username.
    """
    random_int = round(random.random() * 10 ** 6)

    existing_otp = db.session.query(OTP).filter_by(username=username).first()
    if existing_otp is None:
        db.session.add(OTP(otp=random_int, username=username, time=datetime.now()))
    else:
        existing_otp.otp = random_int
        existing_otp.time = datetime.now()
    db.session.commit()

    try:
        message = Message('Your otp', recipients=[username])
        message.body = f"FCC Sizing Software for Create Password is {random_int}"
        mail.send(message)
        return True, 'OTP sent'
    except Exception as e:
        log.error("send_otp failed for %s: %s", username, e, exc_info=True)
        return False, str(e)


def add_user_as_engineer(name, designation):
    """Create an engineerMaster record for a newly registered user."""
    db.session.add(engineerMaster(name=name, designation=designation))
    db.session.commit()


def create_default_project_and_item(user):
    """Create the default project, item, valve, actuator, accessories,
    company, address, and address-project link for a new user.

    Called once immediately after account creation.
    No changes to data structure or relationships.
    """
    fluid_state = fluidState.query.first()

    new_project = projectMaster(
        user=user,
        quoteNo=None,
        projectRef='TBA', enquiryRef='TBA', noise_limit=85, trim_exit_velocity='no',
        enquiryReceivedDate=datetime.today(),
        receiptDate=datetime.today(),
        bidDueDate=datetime.today(),
        revision=0, cur_revno=0,
    )

    new_item = itemMaster(project=new_project, itemNumber=1, alternate='A', revision=0, cur_revno=0)

    new_valve = valveDetailsMaster(
        item=new_item, state=fluid_state, tagNumber='TBA', serialNumber='TBA',
        application='TBA', revision=0, isActive=0, cases_length=5,
        inpres_unit=new_project.pressure_unit,
        outpres_unit=new_project.pressure_unit,
        vaporpres_unit=new_project.pressure_unit,
        criticalpres_unit=new_project.pressure_unit,
        inpipe_unit=new_project.length_unit,
        outpipe_unit=new_project.length_unit,
        valvesize_unit=new_project.length_unit,
        intemp_unit=new_project.temperature_unit,
        viscosity_unit=new_project.viscosity_unit,
    )

    new_actuator = actuatorMaster(item=new_item, revision=0)
    new_accessories = accessoriesData(item=new_item, revision=0)
    new_company = companyMaster(name='FCC', description='Oil and Gas')
    new_address = addressMaster(
        address='Chennai', isActive=1, user=user,
        company=new_company, customerCode='A001',
    )
    new_add_project = addressProject(address=new_address, isCompany=True, project=new_project)

    db.session.add_all([
        new_project, new_item, new_valve, new_actuator, new_accessories,
        new_company, new_address, new_add_project,
    ])
    db.session.commit()
