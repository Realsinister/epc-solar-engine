import csv, os
headers = [
  "manufacturer","model","declared_unit","Wp_module","Wp_per_m2","area_m2",
  "year","PCR","programme_operator","dataset_uuid","version","source",
  "GWP_total_A1A3_per_DU_kgCO2e","GWP_fossil_A1A3_per_DU_kgCO2e",
  "ODP_A1A3_per_DU_kgCFC11e","AP_A1A3_per_DU_molH+e",
  "EP_freshwater_A1A3_per_DU_kgPe","EP_marine_A1A3_per_DU_kgNe","EP_terrestrial_A1A3_per_DU_molNe",
  "POCP_A1A3_per_DU_kgNMVOCe","ADP_mm_A1A3_per_DU_kgSbe","ADP_fossil_A1A3_per_DU_MJ",
  "WDP_A1A3_per_DU_m3w.e.","PERE_A1A3_per_DU_MJ","PERM_A1A3_per_DU_MJ","PERT_A1A3_per_DU_MJ",
  "PENRE_A1A3_per_DU_MJ","PENRM_A1A3_per_DU_MJ","PENRT_A1A3_per_DU_MJ",
  "SM_A1A3_per_DU_kg","RSF_A1A3_per_DU_MJ","NRSF_A1A3_per_DU_MJ",
  "FW_A1A3_per_DU_m3","HWD_A1A3_per_DU_kg","NHWD_A1A3_per_DU_kg","RWD_A1A3_per_DU_kg",
  "CRU_A1A3_per_DU_kg","MFR_A1A3_per_DU_kg","MER_A1A3_per_DU_kg","EEE_A1A3_per_DU_MJ","EET_A1A3_per_DU_MJ"
]
os.makedirs("data", exist_ok=True)
path = os.path.join("data","MANUAL_ENTRY_TEMPLATE.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
  csv.writer(f).writerow(headers)
print(f"Created {path}")
