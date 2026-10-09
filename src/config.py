"""
Configuration parameters for Criticality- and Deadline-Aware Graph Burning.
Based on the research specification for emergency alert dissemination in dynamic networks.
"""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
RESULTS_DIR = BASE_DIR / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
TABLES_DIR = RESULTS_DIR / "tables"

RAW_DATA_FILE = RAW_DATA_DIR / "hospital_lyon_contacts.dat"
DATASET_URL = "https://www.sociopatterns.org/assets/data/hospital_lyon_contacts.dat.gz"

# Dynamic Network Snapshot Configuration
# Aggregate 20-second contact records into 5-minute (300-second) windows
SNAPSHOT_WINDOW_SECONDS = 300

# Node Criticality Mapping (1 to 5)
# MED = Medical Doctor, NUR = Nurse/Paramedical, PAT = Patient, ADM = Administrative
ROLE_CRITICALITY = {
    "MED": 5,   # Doctors / Emergency coordinators (highest priority)
    "NUR": 4,   # Nurses / Response workers
    "PAT": 3,   # Patients / Vulnerable individuals
    "ADM": 2,   # Administrative personnel
    "OTHER": 1  # Ordinary users / unclassified
}

# Criticality threshold: nodes with criticality >= this threshold are defined as "Critical Nodes"
CRITICAL_THRESHOLD = 4

# Alert-Delivery Deadline Formula: Deadline(i) = 7 - Criticality(i)
# Criticality 5 -> Deadline: 2 rounds
# Criticality 4 -> Deadline: 3 rounds
# Criticality 3 -> Deadline: 4 rounds
# Criticality 2 -> Deadline: 5 rounds
# Criticality 1 -> Deadline: 6 rounds
def get_deadline_for_criticality(criticality: int) -> int:
    return max(1, 7 - criticality)

# Default Algorithm Hyperparameters
DEFAULT_BUDGET_K = 5                  # Default number of sources selected
DEFAULT_OVERLAP_WEIGHT = 0.3          # Lambda penalty for redundant coverage
DEFAULT_NUM_ROUNDS = 6                # Propagation horizon rounds

# Experimental Scenarios
SOURCE_BUDGETS = [2, 3, 4, 5, 6]
EDGE_REMOVAL_RATES = [0.0, 0.10, 0.20, 0.30, 0.40]
NUM_REPEATED_RUNS = 5
RANDOM_SEEDS = [42, 101, 2024, 7, 999]
