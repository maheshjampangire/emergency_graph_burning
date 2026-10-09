### Table 1: Dataset and Experimental Configuration

| Item | Setting |
| --- | --- |
| Dataset | SocioPatterns hospital ward |
| Total participants | 75 (11 Doctors, 27 Nurses, 29 Patients, 8 Admin) |
| Contact interval | 20 seconds |
| Graph snapshot duration | 5 minutes (300 s) |
| Experimental horizon | 6 rounds (30 minutes total) |
| Source budgets (K) | 2, 3, 4, 5, and 6 sources |
| Edge-removal failure rates | 0%, 10%, 20%, 30%, and 40% |
| Overlap penalty weight (Lambda) | 0.3 |
| Delivery deadline rule | Deadline(i) = 7 - Criticality(i) |
| Number of repeated runs | 5 |
