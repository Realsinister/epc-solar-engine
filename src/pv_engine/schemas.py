import pandera as pa
import pandas as pd

# Using DataFrameSchema for maximum compatibility across pandera versions
PVModuleSchema = pa.DataFrameSchema({
    "manufacturer": pa.Column(str, nullable=False),
    "name": pa.Column(str, nullable=False),
    "module_power_Wp": pa.Column(float, pa.Check.gt(0), coerce=True),
    "module_area_m2": pa.Column(float, pa.Check.gt(0), coerce=True),
    "GWP_total_A1A3_per_kWp_kgCO2e": pa.Column(float, pa.Check.ge(0), coerce=True),
    "source": pa.Column(str, nullable=True, required=False),
    "version": pa.Column(pa.Object, nullable=True, required=False),
}, strict=False, coerce=True)
