from flask_login import UserMixin
from sqlalchemy import Column, Integer, ForeignKey, String, Boolean, DateTime, Float, or_, \
    BigInteger
from sqlalchemy.orm import relationship, backref
from app.extensions import db
from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime, timedelta


# =============================================================================
# UTILITY / TEST TABLES
# =============================================================================

class newColumn(db.Model):
    __tablename__ = "newCol"

    id = Column(Integer, primary_key=True)
    newRow = Column(Float)
    newCol = Column(Float)


class stemSize(db.Model):
    __tablename__ = "stemSize"

    id = Column(Integer, primary_key=True)
    valveSize = Column(Float)
    stemDia = Column(String(10))


class Test(db.Model):
    __tablename__ = "Test"
    id = Column(Integer, primary_key=True)
    name = Column(String(1000))
    desc = Column(String(1000))
    age = Column(Integer)


# =============================================================================
# ORGANIZATION REFERENCE DATA
# =============================================================================

class companyMaster(db.Model):
    __tablename__ = "companyMaster"

    __mapper_args__ = {
        'polymorphic_identity': 'company',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))
    description = Column(String(300))

    # relationship as parent
    address = relationship('addressMaster', cascade="all,delete",  back_populates='company')


class departmentMaster(db.Model):
    __tablename__ = "departmentMaster"

    __mapper_args__ = {
        'polymorphic_identity': 'department',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    user = relationship("userMaster", back_populates="department")


class designationMaster(db.Model):
    __tablename__ = "designationMaster"

    __mapper_args__ = {
        'polymorphic_identity': 'deisgnation',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    user = relationship("userMaster", back_populates="designation")



class industryMaster(db.Model):
    __tablename__ = "industryMaster"

    __mapper_args__ = {
        'polymorphic_identity': 'industry',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    # relationship as parent
    project = relationship("projectMaster", cascade="all,delete", back_populates="industry")

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = industryMaster.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()



class regionMaster(db.Model):
    __tablename__ = "regionMaster"

    __mapper_args__ = {
        'polymorphic_identity': 'region',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    # relationship as parent
    project = relationship("projectMaster", cascade="all,delete", back_populates="region")

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = regionMaster.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# BORDERLINE - hybrid org/transactional but used as reference for projects
class addressMaster(db.Model):
    __tablename__ = "addressMaster"

    __mapper_args__ = {
        'polymorphic_identity': 'address',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    address = Column(String(300))
    customerCode = Column(String(15))  # to add as A001 to A999 and B001 to B999 and so on.
    isActive = Column(Boolean)

    createdById = Column(Integer, ForeignKey("userMaster.id"))
    user = relationship("userMaster", back_populates="address")

    # relationship as parent
    address_project = relationship('addressProject', cascade="all,delete", back_populates='address')

    # relationship as child
    companyId = Column(Integer, ForeignKey("companyMaster.id"))
    company = relationship("companyMaster", back_populates="address")


class engineerMaster(db.Model):
    __tablename__ = "engineerMaster"
    __mapper_args__ = {
        'polymorphic_identity': 'engineer',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))
    designation = Column(String(300))

    # relationship as parent
    engineer_project = relationship('engineerProject', cascade="all,delete", back_populates='engineer')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = engineerMaster.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class notesMaster(db.Model):
    __tablename__ = "notesMaster"
    __mapper_args__ = {
        'polymorphic_identity': 'note',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    notesNumber = Column(String(10))
    title = Column(String(300))
    content = Column(String(300))


# =============================================================================
# VALVE CONFIGURATION LOOKUPS
# =============================================================================


class fluidState(db.Model):
    __tablename__ = "fluidState"
    __mapper_args__ = {
        'polymorphic_identity': 'state',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

    # relationship as parent
    valve = relationship('valveDetailsMaster', cascade="all,delete", back_populates='state')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = fluidState.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()



class designStandard(db.Model):
    __tablename__ = "designStandard"
    __mapper_args__ = {
        'polymorphic_identity': 'standard',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

    # relationship as parent
    valve = relationship('valveDetailsMaster', back_populates='design')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = designStandard.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()



class valveStyle(db.Model):
    __tablename__ = "valveStyle"
    __mapper_args__ = {
        'polymorphic_identity': 'style',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

    # relationship as parent
    valve = relationship('valveDetailsMaster', back_populates='style')
    valvestylegad = relationship('gadAutomationMaster', back_populates='style')
    gaValveStyle = relationship('gaMasterKey', back_populates='style')
    valveSerValid = relationship('valveDataSeriesValidation', back_populates='valve_style')
    valveffValid = relationship('valveDataffValidation', back_populates='valve_style')
    style_noise = relationship('itemNoiseMaster', back_populates='style')
    style_trimexit = relationship('trimExitVelMaster', back_populates='style')
    cv = relationship('cvTable', back_populates='style')
    rcv = relationship('refCvTable', back_populates='style')

    trimtype_ = relationship('trimType', back_populates='style')
    kc_ = relationship('kcTable', back_populates='style')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = valveStyle.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()



class applicationMaster(db.Model):
    __tablename__ = "applicationMaster"
    __mapper_args__ = {
        'polymorphic_identity': 'application',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = applicationMaster.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()



class ratingMaster(db.Model):
    __tablename__ = "ratingMaster"
    __mapper_args__ = {
        'polymorphic_identity': 'rating',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

    # relationship as parent
    valve = relationship('valveDetailsMaster', back_populates='rating')
    ratinggad = relationship('gadAutomationMaster', back_populates='rating')
    valveSerValid = relationship('valveDataSeriesValidation', back_populates='rating')
    rating_noise = relationship('itemNoiseMaster',  back_populates='rating')
    rating_trimexit = relationship('trimExitVelMaster',  back_populates='rating__')
    pt = relationship('pressureTempRating',  back_populates='rating')
    baffle = relationship('baffleTable', back_populates='rating_baffle')
    cv = relationship('cvTable', back_populates='rating_c')
    rcv = relationship('refCvTable',  back_populates='rating_c')
    packingF = relationship('packingFriction',  back_populates='rating')
    torque = relationship("packingTorque",  back_populates='rating')
    rotaryAct = relationship("shaftRotary", back_populates='rating')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = ratingMaster.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()



class materialMaster(db.Model):
    __tablename__ = "materialMaster"
    __mapper_args__ = {
        'polymorphic_identity': 'material',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    design_name = Column(String(100))
    min_temp = Column(Float)
    max_temp = Column(Float)
    notes = Column(String(100))

    # relationship as parent
    valve = relationship('valveDetailsMaster', back_populates='material')
    pt = relationship('pressureTempRating', back_populates='material')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = materialMaster.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# =============================================================================
# TRIM NOISE LOOKUP TABLES (BORDERLINE)
# =============================================================================

class trimNoiseLiquid(db.Model):
    id = Column(Integer, primary_key=True)
    Aeta = Column(Float)
    Stp = Column(Float)

    trimTypeId = Column(Integer, ForeignKey("trimType.id"))
    trimType__ = relationship('trimType', back_populates='trimnoise_liq_aeta')


class trimNoise(db.Model):
    id = Column(Integer, primary_key=True)
    Aeta = Column(Float)
    Stp = Column(Float)

    trimTypeId = Column(Integer, ForeignKey("trimType.id"))
    trimType__ = relationship('trimType', back_populates='trimnoise_aeta')


# BORDERLINE - derived P-T curve lookup per material + rating combination

class pressureTempRating(db.Model):
    __tablename__ = "pressureTempRating"
    __mapper_args__ = {
        'polymorphic_identity': 'pressureTemp',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    maxTemp = Column(Float)

    pressure = Column(Float)

    # relationship as child
    materialId = Column(Integer, ForeignKey("materialMaster.id"))
    material = relationship("materialMaster", back_populates="pt")

    ratingId = Column(Integer, ForeignKey("ratingMaster.id"))
    rating = relationship("ratingMaster", back_populates="pt")

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = pressureTempRating.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# =============================================================================
# VALVE COMPONENT / DROPDOWN LOOKUPS
# =============================================================================

class endConnection(db.Model):
    __tablename__ = "endConnection"
    __mapper_args__ = {
        'polymorphic_identity': 'endC',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    valveffValid = relationship('valveDataffValidation', back_populates='end_connection')
    endConnectionStd_ = relationship('endConnectionStandard', back_populates='endConnection__')
    endConnection_ = relationship('valveDetailsMaster', back_populates='endConnection__')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = endConnection.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# 19
class endFinish(db.Model):
    __tablename__ = "endFinish"
    __mapper_args__ = {
        'polymorphic_identity': 'endF',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    endFinish_ = relationship('valveDetailsMaster', cascade="all,delete", back_populates='endFinish__')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = endFinish.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# 20
class bonnetType(db.Model):
    __tablename__ = "bonnetType"
    __mapper_args__ = {
        'polymorphic_identity': 'bonnetTyp',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    bonnetType_ = relationship('valveDetailsMaster', back_populates='bonnetType__')
    bonnetTypegad = relationship('gadAutomationMaster', back_populates='bonnetType__')
    valveBonnetValid = relationship('valveDataBonnetValidation', back_populates='bonnet')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = bonnetType.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# 21
class packingType(db.Model):
    __tablename__ = "packingType"
    __mapper_args__ = {
        'polymorphic_identity': 'packingTyp',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    packingType_ = relationship('valveDetailsMaster', cascade="all,delete", back_populates='packingType__')
    # packingT = relationship('packingFriction', cascade="all,delete", back_populates='packingType_')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = packingType.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class trimType(db.Model):
    __tablename__ = "trimType"
    __mapper_args__ = {
        'polymorphic_identity': 'trim',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    trimType_ = relationship('valveDetailsMaster', back_populates='trimType__')
    gaTrim = relationship('gaMasterKey', back_populates='trimType__')
    trim_noise = relationship('itemNoiseMaster',  back_populates='trimType__')
    trimnoise_aeta = relationship('trimNoise',  back_populates='trimType__')
    trimnoise_liq_aeta = relationship('trimNoiseLiquid',  back_populates='trimType__')
    trim_trimexit = relationship('trimExitVelMaster',  back_populates='trimType__')
    trimType_c = relationship('cvTable', back_populates='trimType_')
    trimType_rc = relationship('refCvTable',  back_populates='trimType_')
    trimType_ua = relationship('unbalanceAreaTb', back_populates='trimType_')
    kn = relationship("knValue",  back_populates="trimType_")
    kc_ = relationship("kcTable",  back_populates="trimType_")
    actuatorCase = relationship('actuatorCaseData',back_populates='trimType_')
    vdatanoise = relationship('valveDataNoise', back_populates='trimtype_')
    valveStyleId = Column(Integer, ForeignKey("valveStyle.id"))
    style = relationship('valveStyle', back_populates='trimtype_')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = trimType.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class bodyFFDimension(db.Model):
    __tablename__ = "bodyFFDimension"

    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    bodyFFDimen_ = relationship('valveDetailsMaster', back_populates='bodyFFDimen__')
    valveffValid = relationship('valveDataffValidation', back_populates='ff_dimension')


class flowCharacter(db.Model):  # TODO - Paandi  ............Done
    __tablename__ = "flowCharacter"
    __mapper_args__ = {
        'polymorphic_identity': 'flowC',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    flowCharacter_ = relationship('valveDetailsMaster', cascade="all,delete", back_populates='flowCharacter__')
    char_noise = relationship('itemNoiseMaster', cascade="all,delete", back_populates='flowCharacter__')
    char_trimexit = relationship('trimExitVelMaster', cascade="all,delete", back_populates='flowCharacter__')
    flowCharacter_c = relationship('cvTable', cascade="all,delete", back_populates='flowCharacter_')
    flowCharacter_rc = relationship('refCvTable', cascade="all,delete", back_populates='flowCharacter_')
    actuatorCase = relationship('actuatorCaseData',back_populates='flowCharacter_')
    kn = relationship('knValue', cascade="all,delete", back_populates='flowCharacter_')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = flowCharacter.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# 23
class flowDirection(db.Model):  # TODO - Paandi  ............Done
    __tablename__ = "flowDirection"
    __mapper_args__ = {
        'polymorphic_identity': 'flowD',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    flowDirection_ = relationship('valveDetailsMaster', cascade="all,delete", back_populates='flowDirection__')
    flowdirgad = relationship('gadAutomationMaster', cascade="all,delete", back_populates='flowDirection_')
    dir_noise = relationship('itemNoiseMaster', cascade="all,delete", back_populates='flowDirection__')
    dir_trimexit = relationship('trimExitVelMaster', cascade="all,delete", back_populates='flowDirection__')
    flowDirection_c = relationship('cvTable', cascade="all,delete", back_populates='flowDirection_')
    flowDirection_rc = relationship('refCvTable', cascade="all,delete", back_populates='flowDirection_')
    actuatorCase = relationship('actuatorCaseData',back_populates='flowDirection_')

    kn = relationship('knValue', cascade="all,delete", back_populates='flowDirection_')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = flowDirection.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# 24
class seatLeakageClass(db.Model):  # TODO - Paandi    ..........Done
    __tablename__ = "seatLeakageClass"
    __mapper_args__ = {
        'polymorphic_identity': 'leakage',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))
    leakage_ua = relationship('unbalanceAreaTb', back_populates='seatLeakageClass__')
    seatLeakageClass_ = relationship('valveDetailsMaster', cascade="all,delete", back_populates='seatLeakageClass__')
    seatLoad = relationship('seatLoadForce', cascade="all,delete", back_populates='leakage')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = seatLeakageClass.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# 25
class bonnet(db.Model):
    __tablename__ = "bonnet"
    __mapper_args__ = {
        'polymorphic_identity': 'bonne',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))
    design_name = Column(String(100))
    min_temp = Column(Float)
    max_temp = Column(Float)
    notes = Column(String(100))

    bonnet_ = relationship('valveDetailsMaster', back_populates='bonnet__')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = bonnet.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class nde1(db.Model):
    __tablename__ = "nde1"
    __mapper_args__ = {
        'polymorphic_identity': 'nde',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    nde1_ = relationship('valveDetailsMaster', cascade="all,delete", back_populates='nde1__')


class nde2(db.Model):
    __tablename__ = "nde2"
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    nde2_ = relationship('valveDetailsMaster', cascade="all,delete", back_populates='nde2__')


class shaftRotary(db.Model):
    __tablename__ = "shaftRotary"

    id = Column(Integer, primary_key=True)

    ratingId = Column(Integer, ForeignKey("ratingMaster.id"))
    rating = relationship("ratingMaster", back_populates="rotaryAct")

    valveSize = Column(Float)
    stemDia = Column(String(10))
    valveInterface = Column(String(10))


class shaft(db.Model):  # Stem in globe
    __tablename__ = "shaft"
    __mapper_args__ = {
        'polymorphic_identity': 'shaf',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    design_name = Column(String(100))
    yield_strength = Column(Float)

    shaft_ = relationship('valveDetailsMaster', back_populates='shaft__')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = shaft.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class plug(db.Model):
    __tablename__ = "plug"
    __mapper_args__ = {
        'polymorphic_identity': 'dis',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    design_name = Column(String(100))
    plug_ = relationship('valveDetailsMaster', back_populates='plug__')


class disc(db.Model):
    __tablename__ = "disc"
    __mapper_args__ = {
        'polymorphic_identity': 'dis',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    design_name = Column(String(100))
    disc_ = relationship('valveDetailsMaster', back_populates='disc__')


class seal(db.Model):  # both seat
    __tablename__ = "seal"
    __mapper_args__ = {
        'polymorphic_identity': 'seal',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    design_name = Column(String(100))
    seal_type = Column(String(100))

    seal_ = relationship('valveDetailsMaster',  back_populates='seal__')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = seat.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class seat(db.Model):  # both seat
    __tablename__ = "seat"
    __mapper_args__ = {
        'polymorphic_identity': 'sea',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    design_name = Column(String(100))

    seat_ = relationship('valveDetailsMaster',  back_populates='seat__')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = seat.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class packing(db.Model):
    __tablename__ = "packing"
    __mapper_args__ = {
        'polymorphic_identity': 'pack',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

    packing_ = relationship('valveDetailsMaster', back_populates='packing__')
    packingF = relationship('packingFriction', back_populates='packing_')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = packing.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class balanceSeal(db.Model):  # NDE  # TODO - Paandi
    __tablename__ = "balanceSeal"
    __mapper_args__ = {
        'polymorphic_identity': 'balanceSel',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    balanceSeal_ = relationship('valveDetailsMaster', back_populates='balanceSeal__')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = balanceSeal.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class studNut(db.Model):
    __tablename__ = "studNut"
    __mapper_args__ = {
        'polymorphic_identity': 'stud',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))
    design_name = Column(String(300))
    nace_req = Column(String(300))

    studNut_ = relationship('valveDetailsMaster', back_populates='studNut__')


class gasket(db.Model):
    __tablename__ = "gasket"
    __mapper_args__ = {
        'polymorphic_identity': 'gas',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))
    design_name = Column(String(300))

    gasket_ = relationship('valveDetailsMaster', back_populates='gasket__')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = gasket.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class cageClamp(db.Model):
    __tablename__ = "cageClamp"
    __mapper_args__ = {
        'polymorphic_identity': 'cage',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))
    design_name = Column(String(300))

    cage_ = relationship('valveDetailsMaster', back_populates='cage__')


# To cv table
class balancing(db.Model):
    __tablename__ = "balancing"
    __mapper_args__ = {
        'polymorphic_identity': 'balance',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    balancing_ = relationship('valveDetailsMaster', cascade="all,delete", back_populates='balancing__')
    gaBalancing = relationship('gaMasterKey', cascade="all,delete", back_populates='balancing__')
    balancing_c = relationship('cvTable', cascade="all,delete", back_populates='balancing_')
    balancing_rc = relationship('refCvTable', cascade="all,delete", back_populates='balancing_')
    actuatorCase = relationship('actuatorCaseData',back_populates='balancing_')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = balancing.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# =============================================================================
# VALIDATION RULE TABLES (BORDERLINE)
# =============================================================================

# TODO dropdowns end
class valveDataSeriesValidation(db.Model):
    __tablename__ = "valveDataSeriesValidation"

    id = Column(Integer, primary_key=True)

    valveStyleId = Column(Integer, ForeignKey("valveStyle.id"))
    valve_style = relationship("valveStyle", back_populates="valveSerValid")

    ratingId = Column(Integer, ForeignKey("ratingMaster.id"))
    rating = relationship("ratingMaster", back_populates="valveSerValid")

    min_temperature = Column(String(30))
    valve_series = Column(String(30))


class valveDataffValidation(db.Model):
    __tablename__ = "valveDataffValidation"

    id = Column(Integer, primary_key=True)

    valveStyleId = Column(Integer, ForeignKey("valveStyle.id"))
    valve_style = relationship("valveStyle", back_populates="valveffValid")

    endConnectionId = Column(Integer, ForeignKey("endConnection.id"))
    end_connection = relationship('endConnection', back_populates='valveffValid')

    ffDimensionId = Column(Integer, ForeignKey("bodyFFDimension.id"))
    ff_dimension = relationship('bodyFFDimension', back_populates='valveffValid')

    series = Column(String(30))
    valve_size = Column(String(30))


class valveDataBonnetValidation(db.Model):
    __tablename__ = "valveDataBonnetValidation"

    id = Column(Integer, primary_key=True)

    bonnetId = Column(Integer, ForeignKey("bonnetType.id"))
    bonnet = relationship("bonnetType", back_populates="valveBonnetValid")

    packing = Column(String(100))
    balanceSeal = Column(String(100))
    series = Column(String(30))
    min_temperature = Column(String(30))
    max_temperature = Column(String(30))


# =============================================================================
# ENGINEERING LOOKUP TABLES
# =============================================================================

class pipeArea(db.Model):
    __tablename__ = "pipeArea"
    __mapper_args__ = {
        'polymorphic_identity': 'pipeAre',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    nominalDia = Column(Float)
    nominalPipeSize = Column(Float)
    outerDia = Column(Float)
    thickness = Column(Float)
    area = Column(Float)
    schedule = Column(String(50))

    # rel as parent
    caseI = relationship("caseMaster", back_populates="iPipe")
    # caseO = relationship("caseMaster", back_populates="oPipe")

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = pipeArea.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# BORDERLINE - baffle specification data referenced by selectedBaffles
class baffleTable(db.Model):
    __tablename__ = "baffleTable"

    id = Column(Integer, primary_key=True)
    baffle_size = Column(Float)
    cv = Column(Float)
    no_of_holes = Column(Float)
    hole_dia = Column(Float)
    fd = Column(Float)

    ratingId = Column(Integer, ForeignKey("ratingMaster.id"))
    rating_baffle = relationship('ratingMaster', back_populates='baffle')

    baffle_ = relationship("selectedBaffles", back_populates="baffleCvTable")


# BORDERLINE - Cv lookup table parameterized by trim/flow/rating/style
class cvTable(db.Model):
    __tablename__ = "cvTable"
    __mapper_args__ = {
        'polymorphic_identity': 'cvT',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    valveSize = Column(Float)
    series = Column(String(50))

    # rel as parent
    value = relationship("cvValues", cascade="all,delete", back_populates="cv")
    case = relationship("caseMaster", back_populates="cv")
    torque = relationship("packingTorque", back_populates="cv")

    # rel as child
    trimTypeId = Column(Integer, ForeignKey("trimType.id"))
    trimType_ = relationship('trimType', back_populates='trimType_c')

    flowCharacId = Column(Integer, ForeignKey("flowCharacter.id"))
    flowCharacter_ = relationship('flowCharacter', back_populates='flowCharacter_c')

    flowDirId = Column(Integer, ForeignKey("flowDirection.id"))
    flowDirection_ = relationship('flowDirection', back_populates='flowDirection_c')

    balancingId = Column(Integer, ForeignKey("balancing.id"))
    balancing_ = relationship('balancing', back_populates='balancing_c')

    ratingId = Column(Integer, ForeignKey("ratingMaster.id"))
    rating_c = relationship('ratingMaster', back_populates='cv')

    valveStyleId = Column(Integer, ForeignKey("valveStyle.id"))
    style = relationship('valveStyle', back_populates='cv')


class cvValues(db.Model):
    __tablename__ = "cvValues"
    __mapper_args__ = {
        'polymorphic_identity': 'cvV',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    coeff = Column(String(50))
    one = Column(Float)
    two = Column(Float)
    three = Column(Float)
    four = Column(Float)
    five = Column(Float)
    six = Column(Float)
    seven = Column(Float)
    eight = Column(Float)
    nine = Column(Float)
    ten = Column(Float)

    seatBore = Column(Float)  # taken as discDia for butterfly
    travel = Column(Float)  # taken as rotation for butterfly

    # rel as child
    cvId = Column(Integer, ForeignKey("cvTable.id"))
    cv = relationship('cvTable', back_populates='value')


class refCvTable(db.Model):
    __tablename__ = "refCvTable"

    id = Column(Integer, primary_key=True)
    valveSize = Column(Float)
    series = Column(String(50))

    # rel as parent
    value = relationship("refCvValues", cascade="all,delete", back_populates="cv")
    case = relationship("caseMaster", back_populates="rcv")
    torque = relationship("packingTorque", back_populates="rcv")

    # rel as child
    trimTypeId = Column(Integer, ForeignKey("trimType.id"))
    trimType_ = relationship('trimType', back_populates='trimType_rc')

    flowCharacId = Column(Integer, ForeignKey("flowCharacter.id"))
    flowCharacter_ = relationship('flowCharacter', back_populates='flowCharacter_rc')

    flowDirId = Column(Integer, ForeignKey("flowDirection.id"))
    flowDirection_ = relationship('flowDirection', back_populates='flowDirection_rc')

    balancingId = Column(Integer, ForeignKey("balancing.id"))
    balancing_ = relationship('balancing', back_populates='balancing_rc')

    ratingId = Column(Integer, ForeignKey("ratingMaster.id"))
    rating_c = relationship('ratingMaster', back_populates='rcv')

    valveStyleId = Column(Integer, ForeignKey("valveStyle.id"))
    style = relationship('valveStyle', back_populates='rcv')


class refCvValues(db.Model):
    __tablename__ = "refCvValues"

    id = Column(Integer, primary_key=True)
    coeff = Column(String(50))
    one = Column(Float)
    two = Column(Float)
    three = Column(Float)
    four = Column(Float)
    five = Column(Float)
    six = Column(Float)
    seven = Column(Float)
    eight = Column(Float)
    nine = Column(Float)
    ten = Column(Float)

    seatBore = Column(Float)  # taken as discDia for butterfly
    travel = Column(Float)  # taken as rotation for butterfly

    # rel as child
    cvId = Column(Integer, ForeignKey("refCvTable.id"))
    cv = relationship('refCvTable', back_populates='value')


# BORDERLINE - fluid library; can be project-specific or reused as reference
class fluidProperties(db.Model):
    __tablename__ = "fluidProperties"
    __mapper_args__ = {
        'polymorphic_identity': 'fluidP',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    fluidState = Column(String(100))
    fluidName = Column(String(100))
    specificGravity = Column(Float)
    vaporPressure = Column(Float)
    viscosity = Column(Float)
    criticalPressure = Column(Float)
    molecularWeight = Column(Float)
    specificHeatRatio = Column(Float)
    compressibilityFactor = Column(Float)

    # rel as parent
    case = relationship("caseMaster", cascade="all,delete", back_populates="fluid")
    valve = relationship('valveDetailsMaster', cascade="all,delete", back_populates='fluidproperties')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = fluidProperties.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# BORDERLINE - trim noise parameters per trim type
class valveDataNoise(db.Model):
    __tablename__ = "valveDataNoise"

    id = Column(Integer, primary_key=True)
    valveSize = Column(Float)
    portDia = Column(String(50))
    ratedCv = Column(Float)
    noOfHoles = Column(Float)
    noOfRows = Column(Float)
    totalHoles = Column(Float)
    wettedPerimeter = Column(Float)
    hydraulicDiameter = Column(Float)
    areaOfSingleFlowPassage = Column(Float)
    equivOrificeArea = Column(Float)
    equivOrificeDia = Column(Float)
    hydraulicArea = Column(Float)
    dH = Column(Float)
    fD = Column(Float)

    wettedPerimeterUnit = Column(String(20))
    hydraulicDiameterUnit = Column(String(20))
    areaOfSingleFlowUnit = Column(String(20))
    equivOrificeAreaUnit = Column(String(20))
    equivOrificeDiaUnit = Column(String(20))
    hydraulicAreaUnit = Column(String(20))
    dHUnit = Column(String(20))

    trimTypeId = Column(Integer, ForeignKey("trimType.id"))
    trimtype_ = relationship('trimType', back_populates='vdatanoise')


# BORDERLINE - warning message templates/definitions
class caseWarningMaster(db.Model):
    __tablename__ = "caseWarningMaster"

    id = Column(Integer, primary_key=True)
    warning = Column(String(200))
    display_warning = Column(String(200))
    criteria = Column(String(200))
    recommended_solution = Column(Text)


# =============================================================================
# ACTUATOR SIZE / CLEARANCE REFERENCE TABLES
# =============================================================================

class volumeTankSize(db.Model):
    __tablename__ = 'volumeTankSize'

    id=Column(Integer, primary_key=True)
    size=Column(Integer)


class actuatorClearanceVolume(db.Model):
    __tablename__ = 'actuatorClearanceVolume'

    id=Column(Integer,primary_key=True)
    act_size = Column(String(50))
    clearance_volume = Column(Float)


# =============================================================================
# GA (GENERAL ARRANGEMENT) LOOKUP TABLES (BORDERLINE)
# =============================================================================

# BORDERLINE - GA drawing master keyed by style/trim/balancing
class gaMasterKey(db.Model):
    __tablename__ = "gaMasterKey"

    id = Column(Integer, primary_key=True)
    series = Column(Integer)
    size = Column(String(20))
    ga_no = Column(String(20))
    description = Column(String(100))

    valveStyleId = Column(Integer, ForeignKey("valveStyle.id"))
    style = relationship("valveStyle", back_populates="gaValveStyle")

    trimTypeId = Column(Integer, ForeignKey("trimType.id"))
    trimType__ = relationship('trimType', back_populates='gaTrim')

    balancingId = Column(Integer, ForeignKey("balancing.id"))
    balancing__ = relationship('balancing', back_populates='gaBalancing')


# BORDERLINE - connection standards per valve size
class endConnectionStandard(db.Model):
    __tablename__ = "endConnectionStandard"

    id = Column(Integer, primary_key=True)
    valve_size = Column(String(20))
    standard = Column(String(30))

    endConnectionId = Column(Integer, ForeignKey("endConnection.id"))
    endConnection__ = relationship('endConnection', back_populates='endConnectionStd_')


# BORDERLINE - GA dimension lookup per valve style/direction/rating/bonnet
class gadAutomationMaster(db.Model):
    __tablename__ = "gadAutomationMaster"

    id = Column(Integer, primary_key=True)
    valve_size = Column(String(20))
    series = Column(String(20))
    model_no = Column(String(20))
    adjustable_travelstop = Column(String(20))
    A = Column(String(30))
    B = Column(String(30))
    C = Column(String(30))
    D = Column(String(30))
    E = Column(String(30))
    F = Column(String(30))
    AR = Column(String(30))
    valve_weight = Column(Float)
    actuator_weight = Column(Float)
    total_weight = Column(Float)
    OD = Column(String(30))
    PCD = Column(String(30))
    NXDia = Column(String(30))
    drawgNo = Column(String(30))

    valveStyleId = Column(Integer, ForeignKey("valveStyle.id"))
    style = relationship("valveStyle", back_populates="valvestylegad")

    flowDirId = Column(Integer, ForeignKey("flowDirection.id"))
    flowDirection_ = relationship('flowDirection', back_populates='flowdirgad')

    ratingId = Column(Integer, ForeignKey("ratingMaster.id"))
    rating = relationship('ratingMaster', back_populates='ratinggad')

    bonnetTypeId = Column(Integer, ForeignKey("bonnetType.id"))
    bonnetType__ = relationship('bonnetType', back_populates='bonnetTypegad')


# =============================================================================
# HELP / DOCUMENTATION
# =============================================================================

class helpFolders(db.Model):
    __tablename__ = "helpFolders"

    id = Column(Integer, primary_key=True)
    folder_name = Column(String(200))

    helpFiles = relationship("helpFiles", cascade="all,delete", back_populates="helpFold")


class helpFiles(db.Model):
    __tablename__ = "helpFiles"

    id = Column(Integer, primary_key=True)
    file_name = Column(String(200))
    data = db.Column(db.LargeBinary)

    helpFoldId = Column(Integer, ForeignKey("helpFolders.id"))
    helpFold = relationship('helpFolders', back_populates='helpFiles')


# =============================================================================
# MATERIAL / STRENGTH LOOKUP TABLES
# =============================================================================

class yieldStrength(db.Model):
    __tablename__ = "yieldStrength"

    id = Column(Integer, primary_key=True)
    shaft_material = Column(String(200))
    yield_strength = Column(String(200))


# BORDERLINE - packing friction lookup keyed by rating + packing material
class packingFriction(db.Model):
    __tablename__ = "packingFriction"
    __mapper_args__ = {
        'polymorphic_identity': 'packingF',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    stemDia = Column(Float)
    value = Column(Float)

    # rel as child
    ratingId = Column(Integer, ForeignKey("ratingMaster.id"))
    rating = relationship('ratingMaster', back_populates='packingF')

    packingMaterialId = Column(Integer, ForeignKey("packing.id"))
    packing_ = relationship('packing', back_populates='packingF')

    # rel as parent
    actuatorCase = relationship('actuatorCaseData', cascade="all,delete", back_populates='packingF')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = packingFriction.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# BORDERLINE - packing torque lookup keyed by rating + cvTable
class packingTorque(db.Model):
    __tablename__ = "packingTorque"
    __mapper_args__ = {
        'polymorphic_identity': 'packingT',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    shaftDia = Column(Float)

    # rel as child
    ratingId = Column(Integer, ForeignKey("ratingMaster.id"))
    rating = relationship('ratingMaster', back_populates='torque')

    cvId = Column(Integer, ForeignKey("cvTable.id"))
    cv = relationship('cvTable', back_populates='torque')

    ref_cvId = Column(Integer, ForeignKey("refCvTable.id"))
    rcv = relationship('refCvTable', back_populates='torque')

    # rel as parent
    actuatorCase = relationship('actuatorCaseData', cascade="all,delete", back_populates='packingT')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = packingTorque.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# BORDERLINE - seat load force lookup keyed by leakage class
class seatLoadForce(db.Model):
    __tablename__ = "seatLoadForce"
    __mapper_args__ = {
        'polymorphic_identity': 'seatLoad',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    seatBore = Column(Float)
    value = Column(Float)

    # rel as parent
    actuatorCase = relationship('actuatorCaseData', cascade="all,delete", back_populates='seatLoad')

    leakageClassId = Column(Integer, ForeignKey('seatLeakageClass.id'))
    leakage = relationship('seatLeakageClass', back_populates='seatLoad')

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = seatLoadForce.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# BORDERLINE - seating torque reference table
class seatingTorque(db.Model):
    __tablename__ = "seatingTorque"
    __mapper_args__ = {
        'polymorphic_identity': 'seatTorq',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    valveSize = Column(Float)
    discDia = Column(Float)
    discDia2 = Column(Float)
    cusc = Column(Float)
    cusp = Column(Float)
    softSeatA = Column(Float)
    softSeatB = Column(Float)
    metalSeatA = Column(Float)
    metalSeatB = Column(Float)

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = seatingTorque.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# =============================================================================
# ACCESSORIES CATALOG
# =============================================================================

class positioner(db.Model):
    __tablename__ = "positioner"
    __mapper_args__ = {
        'polymorphic_identity': 'pos',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    manufacturer = Column(String(200))
    series = Column(String(200))
    valve_type = Column(String(200))
    signal = Column(String(200))
    communication = Column(String(200))
    moc = Column(String(200))
    proof_type = Column(String(200))
    explosion_class = Column(String(200))
    diagnostic = Column(String(200))
    cable_entry = Column(String(200))
    pneumatic_entry = Column(String(200))
    lever = Column(String(200))
    acting = Column(String(200))
    certification = Column(String(200))
    model_no = Column(String(300))
    remarks = Column(Text)

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = positioner.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class afr(db.Model):
    __tablename__ = "afr"
    __mapper_args__ = {
        'polymorphic_identity': 'afr_',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    manufacturer = Column(String(200))
    series = Column(String(200))
    moc = Column(String(200))
    drain_type = Column(String(200))
    drain_size = Column(String(200))
    port_thread_type = Column(String(200))
    bracket = Column(String(200))
    model_no = Column(String(200))
    remarks = Column(Text)

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = afr.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class volumeBooster(db.Model):
    __tablename__ = "volumeBooster"

    id = Column(Integer, primary_key=True)
    manufacturer = Column(String(200))
    series = Column(String(200))
    npt_size = Column(String(200))
    moc = Column(String(200))
    soft_parts = Column(String(200))
    model_no = Column(String(200))
    remarks = Column(Text)


class limitSwitch(db.Model):
    __tablename__ = "limitSwitch"
    __mapper_args__ = {
        'polymorphic_identity': 'limitS',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    manufacturer = Column(String(200))
    series = Column(String(200))
    moc = Column(String(200))
    feedback_option = Column(String(200))
    switch_type = Column(String(200))
    switch_make = Column(String(200))
    voltage = Column(String(200))
    proof_type = Column(String(200))
    explosion_class = Column(String(200))
    no_of_switches = Column(String(200))
    cable_entry = Column(String(200))
    tempertaure = Column(String(200))
    model_no = Column(String(200))
    remarks = Column(Text)

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = limitSwitch.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class solenoid(db.Model):
    __tablename__ = "solenoid"
    __mapper_args__ = {
        'polymorphic_identity': 'solen',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    manufacturer = Column(String(200))
    series = Column(String(200))
    valve_type = Column(String(200))
    service = Column(String(200))
    orifice = Column(String(200))
    pneumatic_entry = Column(String(200))
    moc = Column(String(200))
    manual_override = Column(String(200))
    voltage = Column(String(200))
    proof_type = Column(String(200))
    explosion_class = Column(String(200))
    insulation_class = Column(String(200))
    model_no = Column(String(200))
    remarks = Column(Text)

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = solenoid.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class cleaning(db.Model):
    __tablename__ = "cleaning"
    __mapper_args__ = {
        'polymorphic_identity': 'clean',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = cleaning.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class paintCerts(db.Model):
    __tablename__ = "paintCerts"
    __mapper_args__ = {
        'polymorphic_identity': 'paintC',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = paintCerts.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class paintFinish(db.Model):
    __tablename__ = "paintFinish"
    __mapper_args__ = {
        'polymorphic_identity': 'paintF',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = paintFinish.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class certification(db.Model):
    __tablename__ = "certification"
    __mapper_args__ = {
        'polymorphic_identity': 'cert',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = certification.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class positionerSignal(db.Model):
    __tablename__ = "positionerSignal"
    __mapper_args__ = {
        'polymorphic_identity': 'posSignal',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = positionerSignal.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# =============================================================================
# VALVE AREA / PORT AREA LOOKUP TABLES
# =============================================================================

class valveAreaTb(db.Model):
    __tablename__ = "valveAreaTb"
    __mapper_args__ = {
        'polymorphic_identity': 'vAreaTb',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    rating = Column(String(300))
    nominalPipeSize = Column(String(300))
    inMM = Column(String(300))
    inInch = Column(String(300))
    area = Column(String(300))

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = valveAreaTb.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class valveArea(db.Model):
    __tablename__ = "valveArea"
    __mapper_args__ = {
        'polymorphic_identity': 'vArea',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    rating = Column(String(300))
    nominalPipeSize = Column(String(300))
    inMM = Column(String(300))
    inInch = Column(String(300))
    area = Column(String(300))

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = valveArea.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class portArea(db.Model):
    __tablename__ = "portArea"
    __mapper_args__ = {
        'polymorphic_identity': 'pArea',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    model = Column(String(20))
    v_size = Column(String(20))
    seat_bore = Column(String(20))
    travel = Column(String(20))
    trim_type = Column(String(20))
    flow_char = Column(String(20))
    area = Column(String(20))

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = portArea.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


class hwThrust(db.Model):
    __tablename__ = "hwThrust"
    __mapper_args__ = {
        'polymorphic_identity': 'hw',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    failAction = Column(String(20))
    mount = Column(String(20))
    ac_size = Column(String(20))
    max_thrust = Column(String(20))
    dia = Column(String(20))

    @staticmethod
    def update(new_data, id):
        keys = new_data.keys()
        files = hwThrust.query.filter_by(id=id).first()
        for key in keys:
            exec("files.{0} = new_data['{0}'][0]".format(key))
        db.session.commit()


# BORDERLINE - Kn coefficient lookup for noise calculations
class knValue(db.Model):
    __tablename__ = "knValue"
    __mapper_args__ = {
        'polymorphic_identity': 'kn',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)
    portDia = Column(Float)
    value = Column(Float)

    series = Column(String(20))

    # rel as child
    trimTypeId = Column(Integer, ForeignKey("trimType.id"))
    trimType_ = relationship('trimType', back_populates='kn')

    flowCharacId = Column(Integer, ForeignKey("flowCharacter.id"))
    flowCharacter_ = relationship('flowCharacter', back_populates='kn')

    flowDirId = Column(Integer, ForeignKey("flowDirection.id"))
    flowDirection_ = relationship('flowDirection', back_populates='kn')


# =============================================================================
# FLOW CALCULATION COEFFICIENT TABLES (BORDERLINE)
# =============================================================================

class twoPhaseCorrectionFactor(db.Model):
    __tablename__ = "twoPhaseCorrectionFactor"

    id = Column(Integer, primary_key=True)
    vr = Column(Float)
    fm = Column(Float)


# BORDERLINE - Kc factor lookup by trim type + valve style
class kcTable(db.Model):
    __tablename__ = "kcTable"
    __mapper_args__ = {
        'polymorphic_identity': 'kcTable',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)

    minSize = Column(Integer)
    maxSize = Column(Integer)

    minDelP = Column(Integer)
    maxDelP = Column(Integer)
    formula = Column(Integer)
    sigmamR = Column(String(100))

    trimTypeId = Column(Integer, ForeignKey("trimType.id"))
    trimType_ = relationship('trimType', back_populates='kc_')

    valveStyleId = Column(Integer, ForeignKey("valveStyle.id"))
    style = relationship("valveStyle", back_populates="kc_")


class multiHoleDJ(db.Model):
    __tablename__ = "multiHoleDJ"
    __mapper_args__ = {
        'polymorphic_identity': 'multiHoleDJ',
        'confirm_deleted_rows': False
    }
    id = Column(Integer, primary_key=True)

    valve_size = Column(Float)
    l_value = Column(Float)


# BORDERLINE - unbalance area per trim type + leakage class
class unbalanceAreaTb(db.Model):
    __tablename__ = "unbalanceAreaTb"

    id = Column(Integer, primary_key=True)
    seatDia = Column(Float)
    plugDia = Column(Float)
    Ua = Column(Float)

    trimTypeId = Column(Integer, ForeignKey("trimType.id"))
    trimType_ = relationship('trimType', back_populates='trimType_ua')

    leakageClassId = Column(Integer, ForeignKey("seatLeakageClass.id"))
    seatLeakageClass__ = relationship('seatLeakageClass', back_populates='leakage_ua')


# =============================================================================
# CONFIGURATION
# =============================================================================

class ProjectNumberRange(db.Model):
    __tablename__ = "project_number_ranges"

    id = Column(Integer, primary_key=True)
    year = Column(Integer)
    first_project_no = Column(Integer)
    last_project_no = Column(Integer)


# =============================================================================
# PRICING LOOKUP TABLES (BORDERLINE)
# =============================================================================

class bodyPriceMaster(db.Model):
    __tablename__ = "bodyPriceMaster"

    id = Column(Integer, primary_key=True)
    size = Column(Float)
    rating = Column(String(50))
    body_style = Column(String(50))
    material_form = Column(String(50))
    end_connection = Column(String(50))
    weight = Column(Float)
    machining = Column(Float)
    rt100_area=Column(Float)
    rtcritical_area=Column(Float)


class bonnetPriceMaster(db.Model):
    __tablename__ = "bonnetPriceMaster"

    id = Column(Integer, primary_key=True)
    size = Column(Float)
    rating = Column(String(50))
    bonnet_type = Column(String(50))
    material_form = Column(String(50))
    weight = Column(Float)
    machining = Column(Float)
    rt100_area=Column(Float)
    rtcritical_area=Column(Float)


class testingPriceMaster(db.Model):
    __tablename__ = "testingPriceMaster"

    id = Column(Integer, primary_key=True)
    testname=Column(String(50))
    cost=Column(Float)


class castingPriceMaster(db.Model):
    __tablename__ = "castingPriceMaster"

    id = Column(Integer, primary_key=True)
    material_grade=Column(String(50))
    material_form = Column(String(50))
    density=Column(Float)
    base_factor=Column(Float)
    price_l25=Column(Float)
    price_g25=Column(Float)
    machine_factor=Column(Float)
    impact_minus_196c=Column(Boolean)
    impact_minus_50c=Column(Boolean)
    corrosion_g48_a=Column(Boolean)
    corrosion_g28_a=Column(Boolean)
    igc_a262_b=Column(Boolean)
    igc_a262_e=Column(Boolean)
    microstructure_a923_a=Column(Boolean)
    ferrite_e562=Column(Boolean)
    grain_size_e112=Column(Boolean)
    nabl=Column(Boolean)
    special_chemistry=Column(Boolean)
    additional_testbar=Column(Boolean)
    hic=Column(Boolean)
    ssc=Column(Boolean)


class forgingPriceMaster(db.Model):
    __tablename__ = "forgingPriceMaster"

    id = Column(Integer, primary_key=True)
    material_grade=Column(String(50))
    uns_no=Column(String(50))
    material_form = Column(String(30))
    density=Column(Float)
    error_factor=Column(Float)
    rs_kg_below_100mm_dia=Column(Float)
    rs_kg_100_to_200mm_dia=Column(Float)
    rs_kg_above_200mm_dia=Column(Float)
    impact_minus_50c=Column(Boolean)
    impact_minus_196c=Column(Boolean)
    corrosion_g48=Column(Boolean)
    corrosion_g28=Column(Boolean)
    igc_a262_practice_b=Column(Boolean)
    igc_a262_practice_e=Column(Boolean)
    microstructure_a923=Column(Boolean)
    ferrite_e562=Column(Boolean)
    grain_size_e112=Column(Boolean)
    nabl=Column(Boolean)
    special_chemistry=Column(Boolean)
    additional_testbar=Column(Boolean)
    hic=Column(Boolean)
    ssc=Column(Boolean)
