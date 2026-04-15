import json
from flask_login import UserMixin
from sqlalchemy import Column, Integer, ForeignKey, String, Boolean, DateTime, Float, or_, \
    BigInteger
from sqlalchemy.orm import relationship, backref
from app.extensions import db
from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime, timedelta


class JSONList(TypeDecorator):
    """Stores a Python list as a JSON string.
    Replaces PostgreSQL ARRAY — works with both SQLite and PostgreSQL."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return json.loads(value)
            except (ValueError, TypeError):
                return value
        return value


# =============================================================================
# NOISE ANALYSIS RECORDS
# =============================================================================

class itemNoiseCases(db.Model):
    __tablename__ = "itemNoiseCases"

    id = Column(Integer, primary_key=True)

    #inputs
    flowrate = Column(Float)
    ipres = Column(Float)
    opres = Column(Float)
    itemp = Column(Float)
    mol_mass = Column(Float)
    specheat = Column(Float)
    compfact = Column(Float)
    ipipesize = Column(Float)
    opipesize = Column(Float)
    ipipesch = Column(String(50))
    opipesch = Column(String(50))
    ipipe_thick = Column(Float)
    opipe_thick = Column(Float)
    ipipe_dia = Column(Float)
    sound_speed_pipe = Column(Float, nullable=True)
    density_pipe_material = Column(Float, nullable=True)
    sound_speed_air = Column(Float, nullable=True)
    density_air = Column(Float, nullable=True)
    reference_freq = Column(Float, nullable=True)
    std_atm_pres = Column(Float, nullable=True)
    valve_size = Column(Float, nullable=True)
    valve_out_dia = Column(Float, nullable=True)
    rated_cv = Column(Float, nullable=True)
    liq_pres_recovery = Column(Float, nullable=True)
    no_of_holes = Column(Float, nullable=True)
    perimeter_single_flow = Column(Float, nullable=True)
    area_single_flow = Column(Float, nullable=True)
    pressure_drop_ratio = Column(Float, nullable=True)
    head_loss_coeff = Column(Float, nullable=True)
    sum_inletvelocity = Column(Float, nullable=True)
    piping_geo_factor = Column(Float, nullable=True)
    combined_flp = Column(Float, nullable=True)
    valve_style_modifier = Column(Float, nullable=True)
    hydraulic_dia = Column(Float, nullable=True)
    equivalent_circular = Column(Float, nullable=True)
    pi = Column(Float, nullable=True)
    gconst = Column(Float, nullable = True)
    nconst = Column(Float, nullable = True)
    Aeta = Column(Float, nullable = True)
    d_tl = Column(Float, nullable = True)

    #input_Units
    flowrate_unit = Column(String(20))
    ipres_unit = Column(String(20))
    opres_unit = Column(String(20))
    itemp_unit = Column(String(20))
    mol_mass_unit = Column(String(20))
    ipipesize_unit = Column(String(20))
    opipesize_unit = Column(String(20))
    ipipe_thick_unit = Column(String(20))
    opipe_thick_unit = Column(String(20))
    ipipe_dia_unit = Column(String(20))
    sound_speed_pipe_unit = Column(String(20), nullable=True)
    density_pipe_material_unit = Column(String(20), nullable=True)
    sound_speed_air_unit = Column(String(20), nullable=True)
    density_air_unit = Column(String(20), nullable=True)
    reference_freq_unit = Column(String(20), nullable=True)
    std_atm_pres_unit = Column(String(20), nullable=True)
    valve_size_unit = Column(String(20), nullable=True)
    valve_out_dia_unit = Column(String(20), nullable=True)
    perimeter_single_flow_unit = Column(String(20), nullable=True)
    area_single_flow_unit = Column(String(20), nullable=True)
    hydraulic_dia_unit = Column(String(20), nullable=True)
    equivalent_circular_unit = Column(String(20), nullable=True)

    #outputs
    calc_cv = Column(Float, nullable=True)
    diff_pres_ratio = Column(Float, nullable=True)
    pvc = Column(Float, nullable=True)
    xvcc = Column(Float, nullable=True)
    xc = Column(Float, nullable=True)
    alpha = Column(Float, nullable=True)
    xb = Column(Float, nullable=True)
    xce = Column(Float, nullable=True)
    dj = Column(Float, nullable=True)
    regime_no = Column(String(20), nullable=True)
    tvc = Column(Float, nullable=True)
    wm = Column(Float, nullable=True)
    cvc = Column(Float, nullable=True)
    mvc = Column(Float, nullable=True)
    eta = Column(Float, nullable=True)
    wa = Column(Float, nullable=True)
    fb = Column(Float, nullable=True)
    rho2 = Column(Float, nullable=True)
    c2 = Column(Float, nullable=True)
    mo = Column(Float, nullable=True)
    m2 = Column(Float, nullable=True)
    lg = Column(Float, nullable=True)
    lpi = Column(Float, nullable=True)
    mach = Column(Float, nullable=True)
    fr = Column(Float, nullable=True)
    fo = Column(Float, nullable=True)
    fg = Column(Float, nullable=True)
    lpae = Column(Float, nullable=True)

    itemNoiseId = Column(Integer, ForeignKey("itemNoiseMaster.id"))
    itemNoise = relationship('itemNoiseMaster', back_populates='caseNoise')


class itemNoiseMaster(db.Model):
    __tablename__ = "itemNoiseMaster"

    id = Column(Integer, primary_key=True)
    tagno = Column(String(100))
    description = Column(String(100))

    ratingId = Column(Integer, ForeignKey("ratingMaster.id"))
    rating = relationship("ratingMaster", back_populates="rating_noise")

    trimTypeId = Column(Integer, ForeignKey("trimType.id"))
    trimType__ = relationship('trimType', back_populates='trim_noise')

    flowCharacterId = Column(Integer, ForeignKey("flowCharacter.id"))
    flowCharacter__ = relationship('flowCharacter', back_populates='char_noise')

    flowDirectionId = Column(Integer, ForeignKey("flowDirection.id"))
    flowDirection__ = relationship('flowDirection', back_populates='dir_noise')

    valveStyleId = Column(Integer, ForeignKey("valveStyle.id"))
    style = relationship("valveStyle", back_populates="style_noise")

    itemId = Column(Integer, ForeignKey("itemMaster.id"))
    item = relationship("itemMaster", back_populates="itemnoise")

    caseNoise = relationship("itemNoiseCases", cascade="all,delete", back_populates="itemNoise")


# =============================================================================
# TRIM EXIT VELOCITY ANALYSIS RECORDS
# =============================================================================

class trimExitVelMaster(db.Model):
    __tablename__ = "trimExitVelMaster"

    id = Column(Integer, primary_key=True)
    tagno = Column(String(100))
    description = Column(String(100))

    trimTypeId = Column(Integer, ForeignKey("trimType.id"))
    trimType__ = relationship('trimType', back_populates='trim_trimexit')

    flowCharacterId = Column(Integer, ForeignKey("flowCharacter.id"))
    flowCharacter__ = relationship('flowCharacter', back_populates='char_trimexit')

    ratingId = Column(Integer, ForeignKey("ratingMaster.id"))
    rating__ = relationship('ratingMaster', back_populates='rating_trimexit')

    flowDirectionId = Column(Integer, ForeignKey("flowDirection.id"))
    flowDirection__ = relationship('flowDirection', back_populates='dir_trimexit')

    valveStyleId = Column(Integer, ForeignKey("valveStyle.id"))
    style = relationship("valveStyle", back_populates="style_trimexit")

    fluid_type = Column(String(20))
    no_of_stages = Column(Integer)
    no_of_turns = Column(Integer)
    case_type = Column(Boolean)


class trimExitVelCases(db.Model):
    __tablename__ = "trimExitVelCases"

    id = Column(Integer, primary_key=True)
    flowrate = Column(Float)
    flowrate_unit = Column(String(20))
    ipres = Column(Float)
    ipres_unit = Column(String(20))
    opres = Column(Float)
    opres_unit = Column(String(20))
    mol_mass = Column(Float, nullable=True)
    specheat = Column(Float, nullable=True)
    vapor_pres = Column(Float, nullable=True)
    vapor_pres_unit = Column(String(20), nullable=True)
    fl = Column(Float, nullable=True)
    cv = Column(Float, nullable=True)
    kc = Column(Float, nullable=True)
    final_tex = Column(Float, nullable=True)
    case_id = Column(Integer)
    mw = Column(Float, nullable=True)
    z_factor = Column(Float, nullable=True)
    temp = Column(Float, nullable=True)
    temp_unit = Column(String(20), nullable=True)

    itemId = Column(Integer, ForeignKey("itemMaster.id"))
    item = relationship("itemMaster", back_populates="trimexit")

    trimexit = relationship("trimExitVelStages", cascade="all,delete", back_populates="trimCase")
    trimexit_stage = relationship("trimExitVelAllStages", cascade="all,delete", back_populates="trimCase")


class trimExitVelAllStages(db.Model):
    __tablename__ = "trimExitVelAllStages"

    id = Column(Integer, primary_key=True)

    stage_id = Column(Integer)
    final_velocity = Column(Float)
    mach_no = Column(Float)
    power_level = Column(Float)
    noise_level = Column(Float)

    trimCaseId = Column(Integer, ForeignKey("trimExitVelCases.id"))
    trimCase = relationship("trimExitVelCases", back_populates="trimexit_stage")


class trimExitVelStages(db.Model):
    __tablename__ = "trimExitVelStages"

    id = Column(Integer, primary_key=True)
    stage_id = Column(Integer)
    cv_ratio = Column(Float)
    cv_ratio_sq =  Column(Float)
    cv_ratio_sq_inv =  Column(Float)
    dp_percent =  Column(Float)
    stage_cv =  Column(Float)
    dp_actual =  Column(Float)
    flow_area =  Column(Float)
    inter_stage_pres = Column(Float)
    dp_cavitation = Column(Float)
    pres_ratio_stage = Column(Float)
    mach_no_values = Column(Float)
    power_level = Column(Float)

    trimCaseId = Column(Integer, ForeignKey("trimExitVelCases.id"))
    trimCase = relationship("trimExitVelCases", back_populates="trimexit")


# =============================================================================
# USER & AUTHENTICATION
# =============================================================================

class userMaster(UserMixin, db.Model):
    __tablename__ = "userMaster"

    __mapper_args__ = {
        'polymorphic_identity': 'user',
        'confirm_deleted_rows': False
    }

    id = Column(Integer, primary_key=True)
    name = Column(String(1000))
    initial = Column(String(10))
    code = Column(String(20))
    password = Column(String(100))
    employeeId = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    mobile = Column(String(100))
    fccUser = Column(Boolean, index=True)
    tenant_code = Column(String(100), index=True)
    admin = Column(Boolean)
    projType = Column(Integer)
    login_count = Column(Integer, default=0)

    # relationships
    address = relationship('addressMaster', cascade="all,delete",  back_populates='user')
    # TODO 1 - Project Master
    project = relationship("projectMaster", cascade="all,delete", back_populates="user")

    # relationship as child
    departmentId = Column(Integer, ForeignKey("departmentMaster.id"))
    department = relationship("departmentMaster", back_populates="user")

    designationId = Column(Integer, ForeignKey("designationMaster.id"))
    designation = relationship("designationMaster", back_populates="user")


class RequestLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    method = db.Column(db.String(10))
    path = db.Column(db.String(256))
    user_id = db.Column(db.String(64))
    duration = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class OTP(db.Model):
    __tablename__ = "OTP"
    __mapper_args__ = {
        'polymorphic_identity': 'otp',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    username = Column(String(100))
    otp = Column(BigInteger)
    time = Column(DateTime)
    address = Column(String(100), nullable=True)


# =============================================================================
# PROJECT & ITEM HIERARCHY
# =============================================================================

class addressProject(db.Model):
    __tablename__ = "addressProject"

    __mapper_args__ = {
        'polymorphic_identity': 'addressP',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    isCompany = Column(Boolean)

    # child to address
    addressId = Column(Integer, ForeignKey("addressMaster.id"))
    address = relationship("addressMaster", back_populates="address_project")

    # child to project
    projectId = Column(Integer, ForeignKey("projectMaster.id"))
    project = relationship("projectMaster", back_populates="project_address")


class engineerProject(db.Model):
    __tablename__ = "engineerProject"

    __mapper_args__ = {
        'polymorphic_identity': 'engineerP',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    isApplication = Column(Boolean)

    # child to address
    engineerId = Column(Integer, ForeignKey("engineerMaster.id"))
    engineer = relationship("engineerMaster", back_populates="engineer_project")

    # child to project
    projectId = Column(Integer, ForeignKey("projectMaster.id"))
    project = relationship("projectMaster", back_populates="project_engineer")


class projectMaster(db.Model):
    __tablename__ = "projectMaster"

    __mapper_args__ = {
        'polymorphic_identity': 'project',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    projectId = Column(String(100))
    quoteNo = Column(String(100), index=True, unique=True)
    isObsolete = db.Column(db.Boolean, default=True)
    projectRef = Column(String(100))
    enquiryRef = Column(String(100))
    enquiryReceivedDate = Column(DateTime)
    receiptDate = Column(DateTime)
    bidDueDate = Column(DateTime)
    purpose = Column(String(100))
    custPoNo = Column(String(100))
    workOderNo = Column(String(100))
    revisionNo = Column(Integer)
    status = Column(String(100))
    pressureUnit = Column(String(50))
    flowrateUnit = Column(String(50))
    temperatureUnit = Column(String(50))
    lengthUnit = Column(String(50))
    revision = Column(Integer)
    cur_revno = Column(Integer)
    testcase_type = Column(String(50))
    isFccProject = Column(Boolean, nullable=True, index=True)

    # For preferences
    pressure_unit = Column(String(50))
    l_flowrate_type = Column(String(50))
    l_flowrate_unit = Column(String(50))
    g_flowrate_type = Column(String(50))
    g_flowrate_unit = Column(String(50))
    viscosity_type = Column(String(50))
    viscosity_unit = Column(String(50))
    length_unit = Column(String(50))
    temperature_unit = Column(String(50))
    trim_exit_velocity = Column(String(50))
    noise_limit = Column(Integer)

    # relationship as parent
    item = relationship("itemMaster", cascade="all,delete", back_populates="project")
    projectnotes = relationship('projectNotes', cascade="all,delete", back_populates='project')
    projectrevision = relationship('projectRevisionTable', cascade="all,delete", back_populates='project')
    project_address = relationship('addressProject', cascade="all,delete", back_populates='project')
    project_engineer = relationship('engineerProject', cascade="all,delete", back_populates='project')

    # relationship as child
    # TODO - User
    createdById = Column(Integer, ForeignKey("userMaster.id"), index=True)
    user = relationship("userMaster", back_populates="project")
    # TODO - Industry
    IndustryId = Column(Integer, ForeignKey("industryMaster.id"))
    industry = relationship("industryMaster", back_populates="project")
    # TODO - Engineer contract
    regionID = Column(Integer, ForeignKey("regionMaster.id"))
    region = relationship("regionMaster", back_populates="project")

    __table_args__ = (
        UniqueConstraint(
            'isFccProject',
            'quoteNo',
            name='uq_isfcc_quoteno'
        ),
    )

    @property
    def customer_name(self):
        addr = next(
            (a for a in sorted(self.project_address, key=lambda x: x.id, reverse=True)
            if a.isCompany),
            None
        )
        return addr.address.company.name if addr and addr.address and addr.address.company else ''

    @property
    def customer_address(self):
        addr = next(
            (a for a in sorted(self.project_address, key=lambda x: x.id, reverse=True)
            if a.isCompany),
            None
        )
        return addr.address.address if addr and addr.address else ''

    @property
    def enduser_name(self):
        addr = next(
            (a for a in sorted(self.project_address, key=lambda x: x.id, reverse=True)
            if a.isCompany is False),
            None
        )
        return addr.address.company.name if addr and addr.address and addr.address.company else ''

    @property
    def enduser_address(self):
        addr = next(
            (a for a in sorted(self.project_address, key=lambda x: x.id, reverse=True)
            if a.isCompany is False),
            None
        )
        return addr.address.address if addr and addr.address else ''

    @property
    def engineer_name(self):
        eng = next(
            (e for e in sorted(self.project_engineer, key=lambda x: x.id, reverse=True)
            if e.isApplication is False),
            None
        )
        return eng.engineer.name if eng and eng.engineer else ''

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = projectMaster.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class projectRevisionTable(db.Model):
    __tablename__ = "projectRevision"
    __mapper_args__ = {
        'polymorphic_identity': 'projectRevise',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)

    projectId = Column(Integer, ForeignKey("projectMaster.id"))
    project = relationship("projectMaster", back_populates="projectrevision")
    projectRevision = Column(Integer)
    itemId = Column(Integer, ForeignKey("itemMaster.id"))
    item = relationship('itemMaster', back_populates='itemrevision')
    itemRevision = Column(Integer)
    prepared_by = Column(String(100))
    message = Column(String(200))
    tagno = Column(String(100))
    time = Column(DateTime)


class projectNotes(db.Model):
    __tablename__ = "projectNotes"
    __mapper_args__ = {
        'polymorphic_identity': 'projectNote',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    notesNumber = Column(String(300))
    notes = Column(String(300))
    date = Column(DateTime)

    # relationship as child
    projectId = Column(Integer, ForeignKey("projectMaster.id"))
    project = relationship("projectMaster", back_populates="projectnotes")


class itemNotesData(db.Model):
    __tablename__ = "itemNotesData"
    __mapper_args__ = {
        'polymorphic_identity': 'itemNote',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    content = Column(String(300))
    notesNumber = Column(String(300))
    revision = Column(Integer)
    draft_status = Column(Integer)
    category = Column(String(100))

    # rel as child to item
    itemId = Column(Integer, ForeignKey("itemMaster.id"))
    item = relationship('itemMaster', back_populates='notes')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = itemNotesData.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class itemMaster(db.Model):
    __tablename__ = "itemMaster"
    __mapper_args__ = {
        'polymorphic_identity': 'item',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    itemNumber = Column(Integer)
    alternate = Column(String(50))
    standardStatus = Column(Boolean)
    pipeDataStatus = Column(Boolean)

    flowrate_unit = Column(String(20))
    flowrate_unit_liq = Column(String(20))
    flowrate_unit_gas = Column(String(20))
    inpres_unit = Column(String(20))
    outpres_unit = Column(String(20))
    og_outletpres_unit = Column(String(20))
    presdrop_unit = Column(String(20))
    viscosity_unit = Column(String(20))
    intemp_unit = Column(String(20))
    vaporpres_unit = Column(String(20))
    criticalpres_unit = Column(String(20))
    inpipe_unit = Column(String(20))
    outpipe_unit = Column(String(20))
    valvesize_unit = Column(String(20))
    revision = Column(Integer)
    cur_status = Column(String(100))
    cur_revno = Column(Integer, index=True)
    cur_revType = Column(String)
    draft_status = Column(Integer)
    initial_status = Column(Integer)
    tagNo = Column(String(200))

    # rel as parent
    case = relationship("caseMaster", cascade="all,delete", back_populates="item")

    # one-to-one relationship with valve, actuator and accessories, as parent
    valve = relationship("valveDetailsMaster", cascade="all,delete", back_populates="item")
    actuator = relationship("actuatorMaster", cascade="all,delete", back_populates="item")
    accessories = relationship("accessoriesData", cascade="all,delete", back_populates="item")
    notes = relationship("itemNotesData", cascade="all,delete", back_populates="item")
    itemrevision = relationship('projectRevisionTable', back_populates='item')
    itemrevisetable = relationship('itemRevisionTable', cascade="all,delete", back_populates="item")
    trimexit = relationship("trimExitVelCases", cascade="all,delete", back_populates="item")
    itemnoise = relationship("itemNoiseMaster", cascade="all,delete", back_populates="item")
    gadnotemaster = relationship("GadNoteMaster", cascade="all,delete", back_populates="item")
    pricing = relationship("pricingAutomation", cascade="all,delete", back_populates="item")

    # relationship as child
    projectID = Column(Integer, ForeignKey("projectMaster.id"), index=True)
    project = relationship("projectMaster", back_populates="item")

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = itemMaster.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class itemRevisionTable(db.Model):
    __tablename__ = "itemRevision"

    id = Column(Integer, primary_key=True)
    itemId = Column(Integer, ForeignKey("itemMaster.id"))
    item = relationship("itemMaster", back_populates="itemrevisetable")
    itemRevisionNo = Column(Integer)
    status = Column(String(100))
    prepared_by = Column(String(100))
    time = Column(DateTime)
    remarks = Column(String(200))


# =============================================================================
# VALVE DESIGN RECORDS
# =============================================================================

class valveDetailsMaster(db.Model):
    __tablename__ = "valveDetailsMaster"
    __mapper_args__ = {
        'polymorphic_identity': 'valveData',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    quantity = Column(Integer)
    tagNumber = Column(String(150))
    serialNumber = Column(String(50))
    shutOffDelP = Column(Float)
    maxPressure = Column(Float)
    maxTemp = Column(Float)
    minTemp = Column(Float)
    shutOffDelPUnit = Column(String(50))
    maxPressureUnit = Column(String(50))
    maxTempUnit = Column(String(50))
    minTempUnit = Column(String(50))
    bonnetExtDimension = Column(Float)
    bonnetExtensionDimen = Column(String(30))
    application = Column(String(150))
    valveSeries = Column(String(30))
    revision = Column(Integer)
    cvType = Column(Integer)
    solveCase = Column(Integer)
    stages = Column(Integer)
    turns = Column(Integer)
    valveModelNo = Column(String(30))
    bodyFFDimension = Column(String(30))
    draft_status = Column(Integer)
    isActive = Column(Integer)
    cases_length = Column(Integer)

    # units
    flowrate_unit = Column(String(20))
    flowrate_unit_liq = Column(String(20))
    flowrate_unit_gas = Column(String(20))
    inpres_unit = Column(String(20))
    outpres_unit = Column(String(20))
    og_outletpres_unit = Column(String(20))
    presdrop_unit = Column(String(20))
    viscosity_unit = Column(String(20))
    intemp_unit = Column(String(20))
    vaporpres_unit = Column(String(20))
    criticalpres_unit = Column(String(20))
    inpipe_unit = Column(String(20))
    outpipe_unit = Column(String(20))
    valvesize_unit = Column(String(20))

    seatbore = Column(Float) #Trim size
    valve_travel = Column(Float) #valve travel

    # one-to-one relationship with itemMaser
    itemId = Column(Integer, ForeignKey("itemMaster.id"))
    item = relationship("itemMaster", back_populates="valve")

    # rel as child individual
    ratingId = Column(Integer, ForeignKey("ratingMaster.id"))
    rating = relationship("ratingMaster", back_populates="valve")

    materialId = Column(Integer, ForeignKey("materialMaster.id"))
    material = relationship("materialMaster", back_populates="valve")

    designStandardId = Column(Integer, ForeignKey("designStandard.id"))
    design = relationship("designStandard", back_populates="valve")

    valveStyleId = Column(Integer, ForeignKey("valveStyle.id"))
    style = relationship("valveStyle", back_populates="valve")

    fluidStateId = Column(Integer, ForeignKey("fluidState.id"))
    state = relationship("fluidState", back_populates="valve")

    fluidPropertiesId = Column(Integer, ForeignKey("fluidProperties.id"))
    fluidproperties = relationship("fluidProperties", back_populates="valve")

    # rel as child dropdown
    endConnectionId = Column(Integer, ForeignKey("endConnection.id"))
    endConnection__ = relationship('endConnection', back_populates='endConnection_')

    endFinishId = Column(Integer, ForeignKey("endFinish.id"))
    endFinish__ = relationship('endFinish', back_populates='endFinish_')

    bonnetTypeId = Column(Integer, ForeignKey("bonnetType.id"))
    bonnetType__ = relationship('bonnetType', back_populates='bonnetType_')

    packingTypeId = Column(Integer, ForeignKey("packingType.id"))
    packingType__ = relationship('packingType', back_populates='packingType_')

    trimTypeId = Column(Integer, ForeignKey("trimType.id"))
    trimType__ = relationship('trimType', back_populates='trimType_')

    flowCharacterId = Column(Integer, ForeignKey("flowCharacter.id"))
    flowCharacter__ = relationship('flowCharacter', back_populates='flowCharacter_')

    flowDirectionId = Column(Integer, ForeignKey("flowDirection.id"))
    flowDirection__ = relationship('flowDirection', back_populates='flowDirection_')

    seatLeakageClassId = Column(Integer, ForeignKey("seatLeakageClass.id"))
    seatLeakageClass__ = relationship('seatLeakageClass', back_populates='seatLeakageClass_')

    bonnetId = Column(Integer, ForeignKey("bonnet.id"))
    bonnet__ = relationship('bonnet', back_populates='bonnet_')

    bodyFFDimenId = Column(Integer, ForeignKey("bodyFFDimension.id"))
    bodyFFDimen__ = relationship('bodyFFDimension', back_populates='bodyFFDimen_')

    nde1Id = Column(Integer, ForeignKey("nde1.id"))
    nde1__ = relationship('nde1', back_populates='nde1_')

    nde2Id = Column(Integer, ForeignKey("nde2.id"))
    nde2__ = relationship('nde2', back_populates='nde2_')

    shaftId = Column(Integer, ForeignKey("shaft.id"))
    shaft__ = relationship('shaft', back_populates='shaft_')

    discId = Column(Integer, ForeignKey("disc.id"))
    disc__ = relationship('disc', back_populates='disc_')

    seatId = Column(Integer, ForeignKey("seat.id"))
    seat__ = relationship('seat', back_populates='seat_')

    sealId = Column(Integer, ForeignKey("seal.id"))
    seal__ = relationship('seal', back_populates='seal_')

    plugId = Column(Integer, ForeignKey("plug.id"))
    plug__ = relationship('plug', back_populates='plug_')

    packingId = Column(Integer, ForeignKey("packing.id"))
    packing__ = relationship('packing', back_populates='packing_')

    balancingId = Column(Integer, ForeignKey("balancing.id"))
    balancing__ = relationship('balancing', back_populates='balancing_')

    balanceSealId = Column(Integer, ForeignKey("balanceSeal.id"))
    balanceSeal__ = relationship('balanceSeal', back_populates='balanceSeal_')

    studNutId = Column(Integer, ForeignKey("studNut.id"))
    studNut__ = relationship('studNut', back_populates='studNut_')

    gasketId = Column(Integer, ForeignKey("gasket.id"))
    gasket__ = relationship('gasket', back_populates='gasket_')

    cageId = Column(Integer, ForeignKey("cageClamp.id"))
    cage__ = relationship('cageClamp', back_populates='cage_')

    warning__ = relationship('valveDataWarnings', back_populates='valve_warning')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = valveDetailsMaster.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()

    @staticmethod
    def getValveElement(item_element, status):
        if status == 'all':
            return db.session.query(valveDetailsMaster).filter_by(item = item_element).first()
        return db.session.query(valveDetailsMaster).filter_by(item = item_element, revision = status).first()


# =============================================================================
# SIZING CASE RECORDS
# =============================================================================

class selectedBaffles(db.Model):
    __tablename__ = "selectedBaffles"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))

    baffleId = Column(Integer, ForeignKey("baffleTable.id"))
    baffleCvTable = relationship('baffleTable', back_populates='baffle_')
    active = Column(String(10))

    baffle_case = relationship("baffleCaseMaster", cascade="all,delete",  back_populates="baffle_")


class baffleWarnings(db.Model):
    __tablename__ = "baffleWarnings"

    id = Column(Integer, primary_key=True)
    name = Column(String(300))
    criteria = Column(String(300))
    recommended_solution = Column(Text)

    baffleId = Column(Integer, ForeignKey("baffleCaseMaster.id"))
    baffleCase = relationship('baffleCaseMaster', back_populates='warning_')


class baffleCaseMaster(db.Model):
    __tablename__ = "baffleCaseMaster"

    id = Column(Integer, primary_key=True)
    limitCv = Column(Float)
    xSizing = Column(Float)
    inletPressure = Column(Float)
    outletPressure = Column(Float)
    inletPressureUnit = Column(String(50))
    outletPressureUnit = Column(String(50))
    expansionFactor = Column(Float)
    baffleMach = Column(Float)
    valveMach = Column(Float)
    baffleNoise = Column(Float)
    valveDp = Column(Float)
    valveNoise = Column(Float)
    systemNoise = Column(Float)
    baffleNo = Column(Integer)
    active = Column(Integer)

    caseId = Column(Integer, ForeignKey("caseMaster.id"))
    case = relationship('caseMaster', back_populates='case_b')

    selectBaffleId = Column(Integer, ForeignKey("selectedBaffles.id"))
    baffle_ = relationship('selectedBaffles',cascade="all,delete", back_populates='baffle_case')

    warning_ = relationship('baffleWarnings', cascade="all,delete", back_populates='baffleCase')


class valveDataWarnings(db.Model):
    __tablename__ = "valveDataWarnings"

    id = Column(Integer, primary_key=True)
    name = Column(Text)

    valveWarningId = Column(Integer, ForeignKey("valveDetailsMaster.id"))
    valve_warning = relationship('valveDetailsMaster', back_populates='warning__')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = valveDataWarnings.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class caseWarnings(db.Model):
    __tablename__ = "caseWarnings"

    id = Column(Integer, primary_key=True)
    cause = Column(String(200))
    effect = Column(String(200))
    display_warning = Column(String(200))
    action = Column(Text)

    caseId = Column(Integer, ForeignKey("caseMaster.id"))
    case = relationship('caseMaster', back_populates='warning_')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = caseWarnings.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}']".format(key))
        db.session.commit()


class caseMaster(db.Model):
    __tablename__ = "caseMaster"
    __mapper_args__ = {
        'polymorphic_identity': 'case',
        'confirm_deleted_rows': False
    }
    #inputs
    id = Column(Integer, primary_key=True)
    flowrate = Column(Float)
    lflowrate = Column(Float)
    gflowrate = Column(Float)
    lflowinpercent = Column(Float)
    lflowoutpercent = Column(Float)
    gflowinpercent = Column(Float)
    gflowoutpercent = Column(Float)
    lflowtype = Column(String(30))
    gflowtype = Column(String(30))
    inletPressure = Column(Float)
    pressuredrop = Column(Float)
    outletPressure = Column(Float)
    og_outletpres = Column(Float)
    inletTemp = Column(Float)
    vaporPressure = Column(Float)
    specificGravity = Column(Float)
    kinematicViscosity = Column(Float)
    specificHeatRatio = Column(Float)
    mw_sg = Column(String(50))
    molecularWeight = Column(Float)
    compressibility = Column(Float)
    fl = Column(Float)
    fd = Column(Float)
    xt = Column(Float)
    criticalPressure = Column(Float)
    inletPipeSize = Column(Float)
    outletPipeSize = Column(Float)
    valveSize = Column(Float)
    iSch = Column(String)
    oSch = Column(String)
    ipipeStatus = Column(Float)
    opipeStatus = Column(Float)

    #outputs
    calculatedCv = Column(Float)
    calcCvLiq = Column(Float)
    calcCvGas = Column(Float)
    openingPercentage = Column(Float)
    chokedDrop = Column(Float)
    gasChokedDrop = Column(Float)
    Ff = Column(Float)
    Fp = Column(Float)
    Flp = Column(Float)
    kc = Column(Float)
    ar = Column(Float)
    spl = Column(Float)
    reNumber = Column(Float)
    pipeInVel = Column(Float)
    pipeOutVel = Column(Float)
    valveVel = Column(Float)
    tex = Column(Float)
    generated_power = Column(Float)
    allowable_power = Column(Float)
    powerLevel = Column(Float)
    requiredStages = Column(Float)
    x_delp = Column(Float)
    fk = Column(Float)
    y_expansion = Column(Float)
    xtp = Column(Float)
    machNoUp = Column(Float)
    machNoDown = Column(Float)
    machNoValve = Column(Float)
    sonicVelUp = Column(Float)
    sonicVelDown = Column(Float)
    sonicVelValve = Column(Float)
    outletDensity = Column(Float)
    ratedCv = Column(Float)
    seatDia = Column(Float)
    dp_op = Column(String(30))
    vr = Column(Float)
    fm = Column(Float)
    actualGasFlow = Column(Float)
    lflowrate_conv = Column(Float)
    gflowrate_conv = Column(Float)
    liqInletDensity = Column(Float)
    fluid_ = Column(String(100))
    gasViscosity = Column(Float)

    revision = Column(Integer)
    draft_status = Column(Integer)
    flowrateType = Column(String(30))
    # cv_lists = db.Column(ARRAY(db.Float), nullable=True)  # PostgreSQL only
    cv_lists = db.Column(JSONList, nullable=True)

    # rel as child
    inletPipeSchId = Column(Integer, ForeignKey("pipeArea.id"))
    iPipe = relationship('pipeArea', back_populates='caseI', foreign_keys="[caseMaster.inletPipeSchId]")

    valveDiaId = Column(Integer, ForeignKey("cvTable.id"))
    cv = relationship('cvTable', back_populates='case')

    refValveDiaId = Column(Integer, ForeignKey("refCvTable.id"))
    rcv = relationship('refCvTable', back_populates='case')

    itemId = Column(Integer, ForeignKey("itemMaster.id"))
    item = relationship('itemMaster', back_populates='case')

    fluidId = Column(Integer, ForeignKey("fluidProperties.id"))
    fluid = relationship('fluidProperties', back_populates='case')

    case_b = relationship('baffleCaseMaster', cascade="all,delete", back_populates='case')

    warning_ = relationship('caseWarnings', cascade="all,delete", back_populates='case')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = caseMaster.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}']".format(key))
        db.session.commit()


# =============================================================================
# ACTUATOR RECORDS
# =============================================================================

class actuatorMaster(db.Model):
    __tablename__ = "actuatorMaster"
    __mapper_args__ = {
        'polymorphic_identity': 'actuator',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    actuatorType = Column(String(100))
    springAction = Column(String(100))  # Fail Action
    Spring = Column(String(100))
    handWheel = Column(String(100))
    adjustableTravelStop = Column(String(100))
    orientation = Column(String(100))
    availableAirSupplyMin = Column(Float)
    availableAirSupplyMinUnit = Column(String(20))
    availableAirSupplyMax = Column(Float)
    availableAirSupplyMaxUnit = Column(String(20))
    travelStops = Column(String(100))
    setPressure = Column(Float)
    setPressureUnit = Column(String(20))
    shutoffDelP = Column(Float)
    shutoffDelPUnit = Column(String(20))
    actSelectionType = Column(String(20))
    revision = Column(Integer)
    act_modelno = Column(String(20))
    remarks = Column(String(500))
    actuatorModelNo = Column(String(30))
    draft_status = Column(Integer)

    volume_tank = relationship('volumeTank', cascade="all,delete", back_populates='actuator_')

    # rel as parent
    actCase = relationship('actuatorCaseData', cascade="all,delete", back_populates='actuator_')
    rotCase = relationship('rotaryCaseData', cascade="all,delete", back_populates='actuator_')

    # rel as child to item
    itemId = Column(Integer, ForeignKey("itemMaster.id"))
    item = relationship('itemMaster', back_populates='actuator')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = actuatorMaster.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class slidingActuatorData(db.Model):
    __mapper_args__ = {
        'polymorphic_identity': 'slidingAct',
        'confirm_deleted_rows': False
    }
    __tablename__ = "slidingActuatorData"
    id = Column(Integer, primary_key=True)
    actType = Column(String(100))
    failAction = Column(String(100))
    stemDia = Column(Float)
    yokeBossDia = Column(Float)
    actSize = Column(String(100))
    effectiveArea = Column(Float)
    travel = Column(Float)
    Spring = Column(String(100))
    sMin = Column(String(100))
    sMax = Column(String(100))
    springRate = Column(String(100))
    MinSF = Column(String(100))
    MaxSF = Column(String(100))
    MinNAT = Column(Float)
    MaxNAT = Column(Float)
    VO = Column(Float)
    VM = Column(Float)
    remarks = Column(String(500))

    # rel as parent
    actuatorCase = relationship('actuatorCaseData', cascade="all,delete", back_populates='slidingActuator')


class rotaryActuatorData(db.Model):
    __tablename__ = "rotaryActuatorData"
    __mapper_args__ = {
        'polymorphic_identity': 'rotAct',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    actType = Column(String(100))
    failAction = Column(String(100))
    valveInterface = Column(String(100))
    actSize_ = Column(String(100))
    actSize = Column(Float)
    springSet = Column(String(100))
    torqueType = Column(String(100))
    setPressure = Column(String(100))
    start = Column(Float)
    mid = Column(Float)
    end = Column(Float)

    # rel as parent
    actuatorCase = relationship('rotaryCaseData', cascade="all,delete", back_populates='rotaryActuator')


class strokeCase(db.Model):
    __tablename__ = "strokeCase"

    #input
    id = Column(Integer, primary_key=True)
    act_size = Column(String(100))
    act_travel = Column(Float)
    diaphragm_ea = Column(Float)
    lower_benchset = Column(Float)
    upper_benchset = Column(Float)
    spring_rate = Column(Float)
    airsupply_max = Column(Float)
    clearance_vol = Column(Float)
    swept_vol = Column(Float)
    packing_friction = Column(Float)
    draft_status = Column(Integer)

    diaphragm_eaUnit = Column(String(20))
    lower_benchsetUnit = Column(String(20))
    upper_benchsetUnit = Column(String(20))
    spring_rateUnit = Column(String(20))
    airsupply_maxUnit = Column(String(20))
    clearance_volUnit = Column(String(20))
    swept_volUnit = Column(String(20))
    act_travelUnit = Column(String(20))
    packing_frictionUnit = Column(String(20))

    #intermediate results
    piExhaust = Column(Float)
    pfExhaust = Column(Float)
    piFill = Column(Float)
    pfFill = Column(Float)
    combinedCVFill = Column(Float)
    combinedCVExhaust = Column(Float)

    piExhaustUnit = Column(String(20))
    pfExhaustUnit = Column(String(20))
    piFillUnit = Column(String(20))
    pfFillUnit = Column(String(20))

    #final results
    prefillTime = Column(Float)
    totalfillTime = Column(Float)
    preExhaustTime = Column(Float)
    totalExhaustTime = Column(Float)

    preFillUnit = Column(String(20))
    totalFillUnit = Column(String(20))
    preExhaustUnit = Column(String(20))
    totalExhaustUnit = Column(String(20))
    revision = Column(Integer)

    actuatorCaseId = Column(Integer, ForeignKey('actuatorCaseData.id'))
    actuatorCase_ = relationship('actuatorCaseData', back_populates='strokeCase_')

    status = Column(Integer)

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = strokeCase.query.filter_by(id=id).first()
        for key in keys:
            value = new_data[key] if new_data[key] else None
            setattr(files, key, value)
        db.session.commit()


class rotaryCaseData(db.Model):
    __tablename__ = "rotaryCaseData"

    id = Column(Integer, primary_key=True)

    #inputs
    v_size = Column(Float)
    disc_dia = Column(Float)
    shaft_dia = Column(Float)
    max_rot = Column(Float)
    delP = Column(Float)
    bush_coeff = Column(Float)
    csc = Column(Float)
    csv = Column(Float)
    a_factor = Column(Float)
    b_factor = Column(Float)
    pack_coeff = Column(Float)
    radial_coeff = Column(Float)
    Section = Column(Float)
    draft_status = Column(Integer)

    #units
    valveSizeUnit = Column(String(100))
    discDiaUnit = Column(String(100))
    shaftDiaUnit = Column(String(100))
    max_rotUnit = Column(String(100))
    delpUnit = Column(String(100))
    packingRadialUnit = Column(String(100))

    #outputs
    st = Column(Float)
    pt = Column(Float)
    ft = Column(Float)
    bto = Column(Float)
    rto = Column(Float)
    eto = Column(Float)
    btc = Column(Float)
    rtc = Column(Float)
    etc = Column(Float)
    mast = Column(Float)
    setP = Column(Float)
    actSize_ = Column(String(100))
    maxAir = Column(Float)
    springSet = Column(String(100))
    springSt = Column(String(100))
    springMd = Column(String(100))
    springEd = Column(String(100))
    AirSt = Column(String(100))
    AirMd = Column(String(100))
    AirEd = Column(String(100))
    ReqHand = Column(Float)

    #units
    stUnit = Column(String(100))
    ptUnit = Column(String(100))
    ftUnit = Column(String(100))
    btoUnit = Column(String(100))
    rtoUnit = Column(String(100))
    etoUnit = Column(String(100))
    btcUnit = Column(String(100))
    rtcUnit = Column(String(100))
    etcUnit = Column(String(100))
    mastUnit = Column(String(100))
    setPUnit = Column(String(100))
    maxAirUnit = Column(String(100))
    stStartUnit = Column(String(100))
    stMidUnit = Column(String(100))
    stEndUnit = Column(String(100))
    atStartUnit = Column(String(100))
    atMidUnit = Column(String(100))
    atEndUnit = Column(String(100))
    handWheelUnit = Column(String(100))
    revision = Column(Integer)

    actuatorMasterId = Column(Integer, ForeignKey('actuatorMaster.id'))
    actuator_ = relationship('actuatorMaster', back_populates='rotCase')

    rotaryActuatorId = Column(Integer, ForeignKey("rotaryActuatorData.id"))
    rotaryActuator = relationship('rotaryActuatorData', back_populates='actuatorCase')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = rotaryCaseData.query.filter_by(id=id).first()
        if files:
            for key, value in new_data.items():
                if value[0] == "":
                    setattr(files, key, None)
                else:
                    setattr(files, key, value[0])
            db.session.commit()
        else:
            print("---Record not found---")


class volumeTank(db.Model):
    __tablename__ = 'volumeTank'

    id = Column(Integer, primary_key=True)
    # units
    clearance_volume_unit = Column(String(20))
    actuatorAreaUnit = Column(String(20))
    valveTravelUnit = Column(String(20))
    sweptVolumeUnit = Column(String(20))
    total_act_volume_unit = Column(String(20))
    fail_action_req_unit = Column(String(20))
    volume_tank_pres_unit = Column(String(20))
    tank_size_unit = Column(String(20))
    pressure_req_unit = Column(String(20))

    #values
    clearance_volume = Column(Float)
    actuatorArea = Column(Float)
    valveTravel = Column(Float)
    sweptVolume = Column(Float)
    total_act_volume = Column(Float)
    fail_action_req = Column(Float)
    volume_tank_pres = Column(Float)
    vol_tank_size = Column(Integer)
    pressure_req = Column(Float)
    no_of_strokes = Column(Integer)
    revision = Column(Integer)

    # end_of_strokes = db.Column(ARRAY(db.Float), nullable=True)  # PostgreSQL only
    end_of_strokes = db.Column(JSONList, nullable=True)
    warning=Column(Text,nullable=True)

    actuatorMasterId = Column(Integer, ForeignKey('actuatorMaster.id'))
    actuator_ = relationship('actuatorMaster', back_populates='volume_tank')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = volumeTank.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}']".format(key))
        db.session.commit()


class actuatorCaseData(db.Model):
    __tablename__ = "actuatorCaseData"
    __mapper_args__ = {
        'polymorphic_identity': 'actCase',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)

    valveSize = Column(Float)
    seatDia = Column(Float)
    valveTravel = Column(Float)
    iPressure = Column(Float)
    oPressure = Column(Float)
    # sliding
    balancing = Column(String(100))
    unbalanceArea = Column(Float)
    stemDia = Column(Float)
    plugDia = Column(Float)
    unbalanceForce = Column(Float)
    unbalanceForceClose = Column(Float)
    fluidNeg = Column(Float)
    valveThrustClose = Column(Float)
    valveThrustOpen = Column(Float)
    shutOffForce = Column(Float)
    stemArea = Column(Float)
    springWindUp = Column(Float)
    maxSpringLoad = Column(Float)
    setPressure = Column(Float)
    sfMin = Column(Float)
    natMin = Column(Float)
    frictionBand = Column(Float)
    reqHandwheelThrust = Column(String(100))
    thrust = Column(Float)
    act_size = Column(String(100))
    act_travel = Column(Float)
    diaphragm_ea = Column(Float)
    lower_benchset = Column(Float)
    upper_benchset = Column(Float)
    spring_rate = Column(Float)
    airsupply_min = Column(Float)
    airsupply_max = Column(Float)
    knValue = Column(Float)
    packingFriction = Column(Float)
    seatloadFactor = Column(Float)
    shutOffDelP = Column(Float)
    unbalForce = Column(Float)
    negGrad = Column(Float)
    act_VO = Column(Float)
    draft_status = Column(Integer)

    # Units
    valveSizeUnit = Column(String(20))
    seatDiaUnit = Column(String(20))
    unbalanceAreaUnit = Column(String(20))
    stemDiaUnit = Column(String(20))
    plugDiaUnit = Column(String(20))
    valveTravelUnit = Column(String(20))
    packingFrictionUnit = Column(String(20))
    inletPressureUnit = Column(String(20))
    outletPressureUnit = Column(String(20))
    delPShutoffUnit = Column(String(20))
    unbalForceOpenUnit = Column(String(20))
    unbalForceCloseUnit = Column(String(20))
    negativeGradientUnit = Column(String(20))
    delPFlowingUnit = Column(String(20))

    # Output Units
    valveThrustCloseUnit = Column(String(20))
    valveThrustOpenUnit = Column(String(20))
    shutOffForceUnit = Column(String(20))
    stemAreaUnit = Column(String(20))
    actuatorTravelUnit = Column(String(20))
    effectiveAreaUnit = Column(String(20))
    lowerBenchsetUnit = Column(String(20))
    upperBenchSetUnit = Column(String(20))
    springRateUnit = Column(String(20))
    springWindupUnit = Column(String(20))
    maximumSpringLoadUnit = Column(String(20))
    maximumAirSupplyUnit = Column(String(20))
    setPressureUnit = Column(String(20))
    actuatorThrustValveCloseUnit = Column(String(20))
    actuatorThrustValveOpenUnit = Column(String(20))
    frictionBandUnit = Column(String(20))
    reqHandwheelUnit = Column(String(20))
    hwThrustUnit = Column(String(20))
    revision = Column(Integer)

    trimTypeId = Column(Integer, ForeignKey("trimType.id"))
    trimType_ = relationship('trimType', back_populates='actuatorCase')

    balancingId = Column(Integer, ForeignKey("balancing.id"))
    balancing_ = relationship('balancing', back_populates='actuatorCase')

    flowDirectionId = Column(Integer, ForeignKey("flowDirection.id"))
    flowDirection_ = relationship('flowDirection', back_populates='actuatorCase')

    flowCharacterId = Column(Integer, ForeignKey("flowCharacter.id"))
    flowCharacter_ = relationship('flowCharacter', back_populates='actuatorCase')

    # rel as child
    actuatorMasterId = Column(Integer, ForeignKey('actuatorMaster.id'))
    actuator_ = relationship('actuatorMaster', back_populates='actCase')

    packingFrictionId = Column(Integer, ForeignKey("packingFriction.id"))
    packingF = relationship('packingFriction', back_populates='actuatorCase')

    packingTorqueId = Column(Integer, ForeignKey("packingTorque.id"))
    packingT = relationship('packingTorque', back_populates='actuatorCase')

    seatLoadId = Column(Integer, ForeignKey("seatLoadForce.id"))
    seatLoad = relationship('seatLoadForce', back_populates='actuatorCase')

    slidingActuatorId = Column(Integer, ForeignKey("slidingActuatorData.id"))
    slidingActuator = relationship('slidingActuatorData', back_populates='actuatorCase')

    strokeCase_ = relationship('strokeCase', cascade="all,delete",back_populates='actuatorCase_')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = actuatorCaseData.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()

    @staticmethod
    def delete(new_data, id):
        keys = new_data.keys()
        files = actuatorCaseData.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# =============================================================================
# GA DRAWING & DOCUMENTATION RECORDS
# =============================================================================

class GadNoteMaster(db.Model):
    __tablename__ = "gadNoteMaster"

    id = Column(Integer, primary_key=True)
    note = Column(String(300))
    revision = Column(Integer)
    draft_status = Column(Integer)

    itemId = Column(Integer, ForeignKey("itemMaster.id"))
    item = relationship('itemMaster', back_populates='gadnotemaster')


# =============================================================================
# ACCESSORIES SELECTION RECORD
# =============================================================================

class accessoriesData(db.Model):
    __tablename__ = "accessoriesData"
    __mapper_args__ = {
        'polymorphic_identity': 'accData',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)

    manufacturer = Column(String(200))
    model = Column(String(200))
    action = Column(String(200))
    pos_gauge = Column(String(200))
    afr = Column(String(200))
    afr_series = Column(String(200))
    afr_gauge = Column(String(200))
    transmitter = Column(String(200))
    limit = Column(String(200))
    limit_series = Column(String(200))
    proximity = Column(String(200))
    booster = Column(String(200))
    booster_series = Column(String(200))
    pilot_valve = Column(String(200))
    air_lock = Column(String(200))
    air_lock_series = Column(String(200))
    ip_make = Column(String(200))
    ip_model = Column(String(200))
    solenoid_make = Column(String(200))
    solenoid_model = Column(String(200))
    solenoid_action = Column(String(200))
    volume_tank = Column(String(200))
    ip_converter = Column(String(200))
    air_receiver = Column(String(200))
    tubing = Column(String(200))
    fittings = Column(String(200))
    cleaning = Column(String(200))
    certification = Column(String(200))
    paint_finish = Column(String(200))
    paint_cert = Column(String(200))
    sp1 = Column(String(200))
    sp2 = Column(String(200))
    sp3 = Column(String(200))
    rm = Column(String(200))
    hydro = Column(String(200))
    final = Column(String(200))
    paint_inspect = Column(String(200))
    packing_inspect = Column(String(200))
    vt1 = Column(String(200))
    vt2 = Column(String(200))
    pos_remarks = Column(String(500))
    afr_remarks = Column(String(500))
    limit_remarks = Column(String(500))
    boosters_remarks = Column(String(500))
    solenoid_remarks = Column(String(500))
    revision = Column(Integer)
    draft_status = Column(Integer)

    # rel as child
    itemId = Column(Integer, ForeignKey("itemMaster.id"))
    item = relationship('itemMaster', back_populates='accessories')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = accessoriesData.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# =============================================================================
# PRICING RECORDS
# =============================================================================

class pricingAutomation(db.Model):
    __tablename__ = "pricingAutomation"

    id = Column(Integer, primary_key=True)
    valve_factor = Column(Float)
    actuator_factor = Column(Float)
    accessories_factor = Column(Float)
    # tests=Column(ARRAY(String(50)))  # PostgreSQL only
    tests=Column(JSONList)
    revision = Column(Integer)

    itemId = Column(Integer, ForeignKey("itemMaster.id"))
    item=relationship('itemMaster', back_populates='pricing')
