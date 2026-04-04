# Import all models so SQLAlchemy can resolve all string-based relationships
# at startup regardless of which module imports first.

# --- Master Data & Borderline Models ---
from .master import (
    # Utility / Test
    newColumn,
    stemSize,
    Test,

    # Organization Reference
    companyMaster,
    departmentMaster,
    designationMaster,
    industryMaster,
    regionMaster,
    addressMaster,       # borderline
    engineerMaster,
    notesMaster,

    # Valve Configuration Lookups
    fluidState,
    designStandard,
    valveStyle,
    applicationMaster,
    ratingMaster,
    materialMaster,

    # Trim Noise Lookup Tables (borderline)
    trimNoiseLiquid,
    trimNoise,
    pressureTempRating,  # borderline

    # Valve Component / Dropdown Lookups
    endConnection,
    endFinish,
    bonnetType,
    packingType,
    trimType,
    bodyFFDimension,
    flowCharacter,
    flowDirection,
    seatLeakageClass,
    bonnet,
    nde1,
    nde2,
    shaftRotary,
    shaft,
    plug,
    disc,
    seal,
    seat,
    packing,
    balanceSeal,
    studNut,
    gasket,
    cageClamp,
    balancing,

    # Validation Rule Tables (borderline)
    valveDataSeriesValidation,
    valveDataffValidation,
    valveDataBonnetValidation,

    # Engineering Lookup Tables
    pipeArea,
    baffleTable,         # borderline
    cvTable,             # borderline
    cvValues,            # borderline
    refCvTable,          # borderline
    refCvValues,         # borderline
    fluidProperties,     # borderline
    valveDataNoise,      # borderline
    caseWarningMaster,   # borderline

    # Actuator Size / Clearance Reference
    volumeTankSize,
    actuatorClearanceVolume,

    # GA Lookup Tables (borderline)
    gaMasterKey,
    endConnectionStandard,
    gadAutomationMaster,

    # Help / Documentation
    helpFolders,
    helpFiles,

    # Material / Strength Lookup
    yieldStrength,
    packingFriction,     # borderline
    packingTorque,       # borderline
    seatLoadForce,       # borderline
    seatingTorque,       # borderline

    # Accessories Catalog
    positioner,
    afr,
    volumeBooster,
    limitSwitch,
    solenoid,
    cleaning,
    paintCerts,
    paintFinish,
    certification,
    positionerSignal,

    # Valve / Port Area Lookup
    valveAreaTb,
    valveArea,
    portArea,
    hwThrust,

    # Flow Coefficient Tables (borderline)
    knValue,
    twoPhaseCorrectionFactor,
    kcTable,
    multiHoleDJ,
    unbalanceAreaTb,     # borderline

    # Configuration
    ProjectNumberRange,

    # Pricing Lookup Tables (borderline)
    bodyPriceMaster,
    bonnetPriceMaster,
    testingPriceMaster,
    castingPriceMaster,
    forgingPriceMaster,
)

# --- Transactional Models ---
from .transactional import (
    # Noise Analysis
    itemNoiseCases,
    itemNoiseMaster,

    # Trim Exit Velocity Analysis
    trimExitVelMaster,
    trimExitVelCases,
    trimExitVelAllStages,
    trimExitVelStages,

    # User & Auth
    userMaster,
    RequestLog,
    OTP,

    # Project & Item Hierarchy
    addressProject,
    engineerProject,
    projectMaster,
    projectRevisionTable,
    projectNotes,
    itemNotesData,
    itemMaster,
    itemRevisionTable,

    # Valve Design
    valveDetailsMaster,

    # Sizing Cases
    selectedBaffles,
    baffleWarnings,
    baffleCaseMaster,
    valveDataWarnings,
    caseWarnings,
    caseMaster,

    # Actuator
    actuatorMaster,
    slidingActuatorData,
    rotaryActuatorData,
    strokeCase,
    rotaryCaseData,
    volumeTank,
    actuatorCaseData,

    # GA Drawing & Documentation
    GadNoteMaster,

    # Accessories Selection
    accessoriesData,

    # Pricing
    pricingAutomation,
)
