"""Engine column definitions and the view / register / check worksheets."""
import datetime as dt

import engine as E
import inputs as I
import registers as R
import sources_data as SD
from xlkit import *  # noqa: F401,F403

SH = None  # set by build_model.main
SKU_CODES = [k["code"] for k in I.SKUS]


# =============================================================================== engine columns
def engine_columns():
    """(key, header, number format, formula template). Tokens: {c:KEY} same-row column, {in:NAME} scenario input."""
    C = []
    add = lambda k, h, f, t="": C.append((k, h, f, t))
    add("key", "Key", "0")
    add("label", "Case", "@")
    add("scen", "Scen#", "0")
    add("cfg", "Cfg#", "0")
    add("dest", "Dest#", "0")
    add("ct", "Ctr#", "0", "INDEX(cfg_ct,{c:cfg})")
    add("n", "Qty ctr", "0", "INDEX(cfg_n,{c:cfg})")
    add("port", "Port#", "0", "INDEX(dest_port,{c:dest})")
    # drivers
    add("fx", "FX eff", "0.0000", "{in:fx_cbe}*(1-{in:fx_spread})")
    add("supfac", "Supplier factor", "0.00", "1")
    add("vatmode", "VAT mode", "0", "{in:sup_vat_mode}")
    add("s301", "§301 rate", "0.0%", "{in:cus_s301}")
    add("oceanfac", "Ocean factor", "0.000", "1")
    add("pricefac", "Price factor", "0.00", "1")
    add("unitsfac", "Units factor", "0.00", "1")
    add("drayfac", "Dray factor", "0.00", "1")
    add("unloadfac", "Unload factor", "0.00", "1")
    add("dmg", "Damage %", "0.0%", "{in:sel_damage}")
    add("distm", "Buyer margin", "0.0%", "{in:mkt_dist_margin}")
    add("edisc", "E-flute disc", "0.0%", "{in:mkt_eflute_disc}")
    add("credit", "Credit days", "0", "{in:sel_credit_days}")
    add("truckfac", "Truck factor", "0.00", "1")
    add("comm", "Commission", "0.0%", "{in:sel_commission}")
    add("testfac", "Testing factor", "0", "1")
    # units / volume / weight
    for c in SKU_CODES:
        add(f"units_{c}", f"Units {c}", "#,##0", f"INDEX(cfg_u_{c},{{c:cfg}},{{c:scen}})*{{c:unitsfac}}")
    add("U", "Units total", "#,##0", "{c:units_3464}+{c:units_3463}+{c:units_3460}")
    for c in SKU_CODES:
        add(f"vol_{c}", f"m³ {c}", "0.000", f"{{c:units_{c}}}*INDEX(lg_vpu_{c},{{c:scen}})")
    add("V", "m³ total", "0.000", "{c:vol_3464}+{c:vol_3463}+{c:vol_3460}")
    add("kg", "kg total", "#,##0", "{c:units_3464}*INDEX(lg_kpu_3464,{c:scen})+{c:units_3463}*INDEX(lg_kpu_3463,{c:scen})+{c:units_3460}*INDEX(lg_kpu_3460,{c:scen})")
    # supplier
    add("req", "Re-quote %", "0.0%", "{in:sup_requote}")
    for c in SKU_CODES:
        add(f"sup_{c}", f"Supplier USD {c}", "#,##0.00", f"{{c:units_{c}}}*q_price_{c}*(1+{{c:req}})*{{c:supfac}}/{{c:fx}}")
    add("SUP", "Supplier USD", "#,##0.00", "{c:sup_3464}+{c:sup_3463}+{c:sup_3460}")
    add("VAT_CASH", "VAT cash", "#,##0.00", "IF(OR({c:vatmode}=2,{c:vatmode}=3),{c:SUP}*{in:sup_vat_rate},0)")
    add("VAT_ECON", "VAT economic", "#,##0.00", "IF({c:vatmode}=3,{c:VAT_CASH},0)")
    add("tooling", "Tooling USD", "#,##0.00", "{in:sup_tooling_egp}/{c:fx}")
    # origin
    add("orig_ctr", "Origin per-ctr", "#,##0.00",
        "IF({c:ct}=4,{in:ori_lcl_truck}*{c:truckfac}/{c:fx}+{in:ori_lcl_cfs_o},{c:n}*(IF({c:ct}=1,{in:ori_truck_20},{in:ori_truck_40})*{c:truckfac}/{c:fx}"
        "+{in:ori_terminal}+IF({c:ct}=1,{in:ori_othc_20},{in:ori_othc_40})*(1-{in:ori_othc_in_freight})+{in:ori_seal}+{in:ori_inspection}"
        "+{in:ori_dd_days}*IF({c:ct}=1,{in:ori_dd_20},{in:ori_dd_40})+{in:ori_loading_egp}/{c:fx}))")
    add("orig_shp", "Origin per-shpt", "#,##0.00",
        "({in:ori_clearance}+{in:ori_coo})/{c:fx}+{in:ori_bl_fee}+{in:ori_fwd_fee}+{in:ori_qc}+{in:ori_wires}*{in:ori_wire_fee}")
    add("ORIGIN", "ORIGIN", "#,##0.00", "{c:orig_ctr}+{c:orig_shp}")
    # ocean
    add("pdiff", "Port diff", "#,##0", "INDEX(tbl_port_diff,{c:port},{c:scen})")
    add("ocean_ctr", "Ocean freight", "#,##0.00",
        "IF({c:ct}=4,MAX({c:V}*{in:oce_lcl_factor},{c:kg}/1000,1)*{in:oce_lcl_rate}*{c:oceanfac},{c:n}*(INDEX(tbl_ocean_rate,MIN({c:ct},3),{c:scen})+{c:pdiff})*{c:oceanfac})")
    add("OCEAN", "OCEAN incl AMS", "#,##0.00", "{c:ocean_ctr}+{in:oce_ams}")
    # customs value, insurance, duty, fees
    for c in SKU_CODES:
        add(f"cv_{c}", f"Customs value {c}", "#,##0.00", f"{{c:sup_{c}}}*(1+IF({{c:vatmode}}=3,{{in:sup_vat_rate}},0))+{{c:tooling}}*{{c:units_{c}}}/{{c:U}}")
    add("CV", "Customs value", "#,##0.00", "{c:cv_3464}+{c:cv_3463}+{c:cv_3460}")
    add("INS", "Insurance", "#,##0.00", "MAX({in:oce_ins_min},{in:oce_ins_rate}*(1+{in:oce_ins_uplift})*({c:SUP}+{c:tooling}+{c:ORIGIN}+{c:OCEAN}))*(1-{in:oce_ins_in_other})")
    add("duty_rate", "Duty rate", "0.0%", "{in:cus_mfn}+{c:s301}")
    add("DUTY", "Duty", "#,##0.00", "{c:CV}*{c:duty_rate}")
    add("MPF", "MPF", "#,##0.00", "MIN(MAX({c:CV}*{in:cus_mpf_rate},{in:cus_mpf_min}),{in:cus_mpf_max})")
    add("HMF", "HMF", "#,##0.00", "{c:CV}*{in:cus_hmf}")
    add("STB", "STB bond", "#,##0.00", "MAX({in:cus_stb_min},{in:cus_stb_rate}/1000*({c:CV}+{c:DUTY}+{c:MPF}+{c:HMF}))")
    add("US_SHP", "US per-shpt fees", "#,##0.00", "{in:cus_broker}+{in:cus_isf}+{in:cus_do_fee}+{c:STB}+{in:cus_isf_bond}")
    add("CFC", "PANYNJ CFC", "#,##0.00", "IF({c:port}=1,{in:cus_cfc}*INDEX(ct_teu,{c:ct})*{c:n}*(1-{in:cus_cfc_in_freight}),0)")
    add("EXAM", "Exam", "#,##0.00", "IF({c:ct}=4,1,{c:n})*({in:cus_exam}+{in:cus_exam_dray})")
    add("DEM", "Demurrage", "#,##0.00", "IF({c:ct}=4,1,{c:n})*{in:cus_dem_days}*{in:cus_dem_rate}")
    add("US_CTR", "US per-ctr", "#,##0.00", "{c:CFC}+{c:EXAM}+{c:DEM}")
    # delivery
    add("DELIV", "Delivery", "#,##0.00",
        "IF({c:ct}=4,({in:dra_lcl_cfs_d}+{in:dra_lcl_deliv})*{c:drayfac},{c:n}*(INDEX(tbl_dest_line,{c:dest},{c:scen})*{c:drayfac}*(1+{in:dra_fsc})"
        "+INDEX(tbl_dest_tolls,{c:dest},{c:scen})+{in:dra_chassis_days}*INDEX(tbl_dest_chassis,{c:dest},{c:scen})*(1-{in:dra_chassis_in_dray})"
        "+{in:dra_wait_hours}*{in:dra_wait_rate}+{in:dra_split}+{in:dra_prepull}+{in:dra_dryrun}))")
    add("UNLOAD", "Unloading", "#,##0.00", "IF({c:ct}=4,0,{c:n}*IF({c:ct}=1,{in:dra_unload_20},{in:dra_unload_40})*{c:unloadfac}*(1-{in:dra_unload_in_dray}))")
    add("COGS", "DELIVERED COGS", "#,##0.00",
        "{c:SUP}+{c:VAT_ECON}+{c:tooling}+{c:ORIGIN}+{c:OCEAN}+{c:INS}+{c:DUTY}+{c:MPF}+{c:HMF}+{c:US_SHP}+{c:US_CTR}+{c:DELIV}+{c:UNLOAD}")
    add("shared_space", "Shared (cube)", "#,##0.00", "{c:orig_ctr}+{c:OCEAN}+{c:US_CTR}+{c:DELIV}+{c:UNLOAD}")
    add("shared_admin", "Shared (units)", "#,##0.00", "{c:orig_shp}+{c:US_SHP}")
    for c in SKU_CODES:
        add(f"cost_{c}", f"Cost {c}", "#,##0.00",
            f"{{c:sup_{c}}}*(1+IF({{c:vatmode}}=3,{{in:sup_vat_rate}},0))+{{c:tooling}}*{{c:units_{c}}}/{{c:U}}+{{c:cv_{c}}}*{{c:duty_rate}}"
            f"+({{c:MPF}}+{{c:HMF}})*{{c:cv_{c}}}/{{c:CV}}+{{c:INS}}*{{c:sup_{c}}}/{{c:SUP}}+{{c:shared_space}}*{{c:vol_{c}}}/{{c:V}}+{{c:shared_admin}}*{{c:units_{c}}}/{{c:U}}")
    add("alloc_chk", "Alloc check", "0.000000", "{c:cost_3464}+{c:cost_3463}+{c:cost_3460}-{c:COGS}")
    for c in SKU_CODES:
        add(f"sale_{c}", f"Saleable {c}", "#,##0", f"{{c:units_{c}}}*(1-{{c:dmg}})")
    add("SALE", "Saleable total", "#,##0", "{c:sale_3464}+{c:sale_3463}+{c:sale_3460}")
    for c in SKU_CODES:
        add(f"cpb_{c}", f"Cost/saleable box {c}", "0.0000", f"IF({{c:sale_{c}}}>0,{{c:cost_{c}}}/{{c:sale_{c}}},0)")
    for c in SKU_CODES:
        add(f"price_{c}", f"Price {c}", "0.0000",
            f"INDEX(in_mkt_listing_{c},1,{{c:scen}})*(1-IF(sku_flute_{c}=\"B\",{{c:edisc}},0))*(1-{{c:distm}})*{{c:pricefac}}")
    add("REV", "Revenue", "#,##0.00", "{c:sale_3464}*{c:price_3464}+{c:sale_3463}*{c:price_3463}+{c:sale_3460}*{c:price_3460}")
    add("GP", "Gross profit", "#,##0.00", "{c:REV}-{c:COGS}")
    add("GM", "Gross margin", "0.0%", "IF({c:REV}>0,{c:GP}/{c:REV},0)")
    add("var_pct", "Variable selling %", "0.0%", "{c:comm}+{in:sel_processing}+{in:sel_bad_debt}")
    add("SELL_VAR", "Selling variable", "#,##0.00", "{c:REV}*{c:var_pct}")
    add("SELL_FIX", "Selling fixed", "#,##0.00", "{in:sel_testing}*{c:testfac}+{in:sel_admin}")
    # cash timeline
    add("t1", "Day export", "0", "{in:sup_lead_days}")
    add("t2", "Day US entry", "0", "{c:t1}+{in:oce_transit}+IF({c:ct}=4,{in:oce_lcl_extra_days},0)")
    add("t3", "Day delivery", "0", "{c:t2}+2+{in:cus_dem_days}")
    add("t4", "Day customer pays", "0", "{c:t3}+{c:credit}")
    add("tref", "Day VAT refund", "0", "{c:t1}+{in:sup_vat_lag}")
    add("adv", "Advance %", "0%", "{in:sup_advance}")
    add("out0", "Cash before shipment", "#,##0.00", "{c:adv}*({c:SUP}+{c:VAT_CASH})+{c:tooling}+{in:sel_testing}*{c:testfac}")
    add("out1", "Cash at export", "#,##0.00", "(1-{c:adv})*({c:SUP}+{c:VAT_CASH})+{c:ORIGIN}+{c:OCEAN}+{c:INS}")
    add("out2", "Cash before US release", "#,##0.00", "{c:DUTY}+{c:MPF}+{c:HMF}+{c:US_SHP}+{c:US_CTR}")
    add("out3", "Cash at delivery", "#,##0.00", "{c:DELIV}+{c:UNLOAD}")
    add("vatref", "VAT refund", "#,##0.00", "IF({c:vatmode}=2,{c:VAT_CASH},0)")
    add("vatdays", "VAT $-days", "#,##0", "IF({c:vatmode}=2,{c:adv}*{c:VAT_CASH}*({c:tref}-0)+(1-{c:adv})*{c:VAT_CASH}*({c:tref}-{c:t1}),0)")
    add("nonvatdays", "Other $-days", "#,##0",
        "({c:out0}-{c:adv}*{c:vatref})*({c:t4}-0)+({c:out1}-(1-{c:adv})*{c:vatref})*({c:t4}-{c:t1})+{c:out2}*({c:t4}-{c:t2})+{c:out3}*({c:t4}-{c:t3})")
    add("FIN", "Financing cost", "#,##0.00", "{in:sel_fin_rate}/365*({c:vatdays}+{c:nonvatdays})")
    add("cum0", "Cum t0", "#,##0", "{c:out0}-IF({c:tref}<=0,{c:vatref},0)")
    add("cum1", "Cum t1", "#,##0", "{c:out0}+{c:out1}-IF({c:tref}<={c:t1},{c:vatref},0)")
    add("cum2", "Cum t2", "#,##0", "{c:out0}+{c:out1}+{c:out2}-IF({c:tref}<={c:t2},{c:vatref},0)")
    add("cum3", "Cum t3", "#,##0", "{c:out0}+{c:out1}+{c:out2}+{c:out3}-IF({c:tref}<={c:t3},{c:vatref},0)")
    add("PEAK", "Peak working capital", "#,##0.00", "MAX({c:cum0},{c:cum1},{c:cum2},{c:cum3})")
    add("CASH_TOTAL", "Total cash outflow", "#,##0.00", "{c:out0}+{c:out1}+{c:out2}+{c:out3}")
    add("CONTRIB", "Contribution", "#,##0.00", "{c:GP}-{c:SELL_VAR}-{c:SELL_FIX}-{c:FIN}")
    add("CM", "Contribution margin", "0.0%", "IF({c:REV}>0,{c:CONTRIB}/{c:REV},0)")
    add("f_be", "Break-even price factor", "0.000", "IF({c:REV}>0,({c:COGS}+{c:SELL_FIX}+{c:FIN})/({c:REV}*(1-{c:var_pct})),0)")
    add("avg_cpb", "Avg cost/saleable box", "0.0000", "IF({c:SALE}>0,{c:COGS}/{c:SALE},0)")
    add("avg_price", "Avg price", "0.0000", "IF({c:SALE}>0,{c:REV}/{c:SALE},0)")
    for c in SKU_CODES:
        add(f"a_{c}", f"a {c}", "0.0000",
            f"IF({{c:sup_{c}}}>0,({{c:sup_{c}}}*IF({{c:vatmode}}=3,{{in:sup_vat_rate}},0)+{{c:cv_{c}}}*{{c:duty_rate}}+({{c:MPF}}+{{c:HMF}})*{{c:cv_{c}}}/{{c:CV}}+{{c:INS}}*{{c:sup_{c}}}/{{c:SUP}})/{{c:sup_{c}}},0)")
    for c in SKU_CODES:
        add(f"o_{c}", f"o {c}", "0.0000", f"IF({{c:units_{c}}}>0,({{c:cost_{c}}}-{{c:sup_{c}}}*(1+{{c:a_{c}}}))/{{c:units_{c}}},0)")
    for c in SKU_CODES:
        add(f"maxexw_{c}", f"Max EXW EGP {c} @GM target", "0.000",
            f"IF({{c:units_{c}}}>0,({{c:price_{c}}}*(1-thr_gm_go)*(1-{{c:dmg}})-{{c:o_{c}}})/(1+{{c:a_{c}}})*{{c:fx}}/((1+{{c:req}})*{{c:supfac}}),\"\")")
    add("mpf_marg", "MPF marginal", "0.0000%", "IF(AND({c:CV}*{in:cus_mpf_rate}>{in:cus_mpf_min},{c:CV}*{in:cus_mpf_rate}<{in:cus_mpf_max}),{in:cus_mpf_rate},0)")
    add("ins_marg", "Ins marginal", "#,##0.00", "IF({c:INS}>{in:oce_ins_min},{in:oce_ins_rate}*(1+{in:oce_ins_uplift})*{c:SUP},0)")
    add("A_lin", "Supplier-linked cost", "#,##0.00", "({c:SUP}+{c:VAT_ECON})*(1+{c:duty_rate}+{in:cus_hmf}+{c:mpf_marg})+{c:ins_marg}")
    add("g_t", "Supplier scale @GM target", "0.000", "IF({c:A_lin}>0,({c:REV}*(1-thr_gm_go)-({c:COGS}-{c:A_lin}))/{c:A_lin},0)")
    add("g_0", "Supplier scale @GM 0", "0.000", "IF({c:A_lin}>0,({c:REV}-({c:COGS}-{c:A_lin}))/{c:A_lin},0)")
    add("chg_gm_t", "Supplier price chg needed (GM target)", "0.0%", "(1+{c:req})*{c:supfac}*{c:g_t}-1")
    add("chg_gm_0", "Supplier price chg needed (GM 0)", "0.0%", "(1+{c:req})*{c:supfac}*{c:g_0}-1")
    add("max_ocean", "Max ocean $/ctr (GM target)", "#,##0", "IF({c:n}>0,({c:REV}*(1-thr_gm_go)-({c:COGS}-{c:ocean_ctr}))/{c:n},\"\")")
    add("var_u", "Variable $/unit", "0.0000", "IF({c:U}>0,({c:SUP}+{c:VAT_ECON}+{c:DUTY}+{c:MPF}+{c:HMF})/{c:U},0)")
    add("fixed", "Fixed $", "#,##0.00", "{c:COGS}-{c:var_u}*{c:U}")
    add("p_u", "Revenue $/unit shipped", "0.0000", "IF({c:U}>0,{c:REV}/{c:U},0)")
    add("u_be_t", "Units needed (GM target)", "#,##0", "IF({c:p_u}*(1-thr_gm_go)-{c:var_u}>0,{c:fixed}/({c:p_u}*(1-thr_gm_go)-{c:var_u}),\"n/a\")")
    add("u_be_0", "Units needed (GM 0)", "#,##0", "IF({c:p_u}-{c:var_u}>0,{c:fixed}/({c:p_u}-{c:var_u}),\"n/a\")")
    add("fits", "Load fits?", "General", "INDEX(cfg_fits,{c:cfg},{c:scen})")
    add("lenutil", "Length util", "0.0%", "IF({c:ct}=4,\"\",INDEX(cfg_lenutil,{c:cfg},{c:scen}))")
    add("unitflag", "Note", "General", "IF({c:unitsfac}>1,\"Check fit (units scaled up)\",\"\")")
    return C


def S(key):
    return f"INDEX(eng_{key},sel_row)"


# =============================================================================== dashboard
def build_dashboard(book):
    ws = book.ws(SH["dash"])
    title(ws, "BigBoxPizza – Egypt→US pizza-box import: Executive Dashboard",
          "Change the three selectors (yellow). Every figure below is a formula on the engine. Evidence status of inputs is shown on each input sheet and in the Assumptions Register.")
    set_widths(ws, {"A": 46, "B": 18, "C": 18, "D": 18, "E": 18, "F": 18, "G": 30})
    r = section(ws, 4, "Selections", 7)
    put(ws, 5, 1, "Scenario (1 = LOW, 2 = BASE, 3 = STRESS)", bold=True)
    inp_cell(ws, 5, 2, 2, "0")
    calc_cell(ws, 5, 3, '=CHOOSE(B5,"LOW / optimistic","BASE","STRESS")', bold=True)
    list_validation(ws, "B5", [1, 2, 3])
    put(ws, 6, 1, "Shipment configuration (1–10)", bold=True)
    inp_cell(ws, 6, 2, 1, "0")
    calc_cell(ws, 6, 3, "=INDEX(cfg_name,B6)")
    ws.merge_cells("C6:G6")
    list_validation(ws, "B6", list(range(1, len(I.CONFIGS) + 1)))
    put(ws, 7, 1, "Destination (1–5)", bold=True)
    inp_cell(ws, 7, 2, 1, "0")
    calc_cell(ws, 7, 3, '=INDEX(dest_gw,B7)&" → "&INDEX(dest_name,B7)')
    ws.merge_cells("C7:G7")
    list_validation(ws, "B7", list(range(1, len(I.DESTINATIONS) + 1)))
    put(ws, 8, 1, "Engine row (calculated)")
    calc_cell(ws, 8, 2, "=MATCH(B5*1000+B6*10+B7,eng_key,0)", "0")
    put(ws, 9, 1, "Valuation date", bold=True)
    inp_cell(ws, 9, 2, dt.date(2026, 10, 16), "yyyy-mm-dd")
    book.name("sel_scen", ws.title, "B5")
    book.name("sel_cfg", ws.title, "B6")
    book.name("sel_dest", ws.title, "B7")
    book.name("sel_row", ws.title, "B8")
    book.name("val_date", ws.title, "B9")
    r = section(ws, 11, "Verdict", 7)
    put(ws, 12, 1, "Analyst verdict (see report §18)", bold=True)
    c = put(ws, 12, 2, "NO-GO under modeled conditions for the quoted NFC transaction. Do not pay any advance. Re-open only if the stated re-entry conditions are met (report §18–19).", wrap=True, font=F_WARN)
    ws.merge_cells("B12:G12")
    ws.row_dimensions[12].height = 32
    put(ws, 13, 1, "Threshold test for the selected case (formula)", bold=True)
    calc_cell(ws, 13, 2, '=IF(AND(D49="PASS",D50="PASS",D51="PASS",D52="PASS",D53="PASS",D54="PASS",D55="PASS"),"GO thresholds met",IF(AND(D49<>"PASS",C49>=thr_gm_cond),"CONDITIONAL – some thresholds unmet","NO-GO – thresholds unmet"))', bold=True)
    ws.merge_cells("B13:G13")
    book.name("dash_threshold", ws.title, "B13")
    # KPIs
    r = section(ws, 15, "Key results – selected case (USD unless stated)", 7)
    header(ws, 16, ["Metric", "Value", "3464", "3463", "3460", "Unit", "Note"])
    kpis = [
        ("Units shipped", S("U"), [S("units_3464"), S("units_3463"), S("units_3460")], FMT_INT, "boxes", ""),
        ("Saleable units (after damage/rejection)", S("SALE"), [S("sale_3464"), S("sale_3463"), S("sale_3460")], FMT_INT, "boxes", ""),
        ("Containers", S("n"), None, "0", "", "=INDEX(cfg_name,sel_cfg)"),
        ("Load fits physically?", f'=IF({S("fits")},"YES","NO – does not fit")', None, None, "", "PROVISIONAL geometry"),
        ("DELIVERED COST per saleable box", S("avg_cpb"), [S("cpb_3464"), S("cpb_3463"), S("cpb_3460")], FMT_USD4, "USD/box", "Customer-delivered, fully landed"),
        ("Delivered cost per 1,000 boxes", f'={S("avg_cpb")}*1000', [f"={S('cpb_' + c)}*1000" for c in SKU_CODES], FMT_USD, "USD/1,000", ""),
        ("Delivered cost per box in EGP", f'={S("avg_cpb")}*{S("fx")}', [f"={S('cpb_' + c)}*{S('fx')}" for c in SKU_CODES], FMT_NUM3, "EGP/box", "at scenario FX"),
        ("Achievable wholesale price (benchmark)", S("avg_price"), [S("price_3464"), S("price_3463"), S("price_3460")], FMT_USD4, "USD/box", "Derived – not a buyer quote"),
        ("Total delivered COGS", S("COGS"), None, FMT_USD, "USD", ""),
        ("Revenue at benchmark price", S("REV"), None, FMT_USD, "USD", ""),
        ("Gross profit", S("GP"), None, FMT_USD, "USD", ""),
        ("Gross margin", S("GM"), None, FMT_PCT, "%", "(P − COGS)/P"),
        ("Contribution after selling & financing", S("CONTRIB"), None, FMT_USD, "USD", ""),
        ("Contribution margin", S("CM"), None, FMT_PCT, "%", ""),
        ("Price increase needed to break even", f'={S("f_be")}-1', None, FMT_PCT, "%", "contribution = 0"),
        ("Supplier price change needed for target GM", S("chg_gm_t"), None, FMT_PCT, "% vs quote", "linearised"),
        ("Section 301 duty in this case", S("DUTY"), None, FMT_USD, "USD", "12.5% of customs value (BASE)"),
        ("Cash required before shipment", S("out0"), None, FMT_USD, "USD", "advance + VAT + testing"),
        ("Cash required at export", S("out1"), None, FMT_USD, "USD", "balance + origin + freight + insurance"),
        ("Cash required before US release", S("out2"), None, FMT_USD, "USD", "duty + fees"),
        ("Cash required at delivery", S("out3"), None, FMT_USD, "USD", "drayage + unloading"),
        ("TOTAL transaction cash outflow", S("CASH_TOTAL"), None, FMT_USD, "USD", "incl. recoverable VAT"),
        ("PEAK working capital", S("PEAK"), None, FMT_USD, "USD", "before customer receipt"),
    ]
    rr = 17
    for lab, f, per, fm, unit, note in kpis:
        put(ws, rr, 1, lab, bold=lab.isupper() or lab.startswith("DELIVERED"))
        calc_cell(ws, rr, 2, f if f.startswith("=") else "=" + f, fm, bold=True)
        if per:
            for j, pf in enumerate(per):
                calc_cell(ws, rr, 3 + j, pf if pf.startswith("=") else "=" + pf, fm)
        put(ws, rr, 6, unit)
        if note.startswith("="):
            calc_cell(ws, rr, 7, note)
        else:
            put(ws, rr, 7, note, wrap=True)
        ws.cell(row=rr, column=2).fill = FILL_KPI
        rr += 1
    # thresholds
    rr = 47
    section(ws, rr, "Go / no-go threshold tests (provisional thresholds – edit in yellow)", 7)
    header(ws, rr + 1, ["Test", "Threshold", "Actual", "Result", "", "", "Basis"])
    tests = [
        ("Gross margin at benchmark price ≥", "thr_gm_go", S("GM"), FMT_PCT, ">=", "Provisional: 25% GO; 15% CONDITIONAL floor"),
        ("Contribution margin ≥", "thr_cm_min", S("CM"), FMT_PCT, ">=", "After commission, bad debt, testing, admin, financing"),
        ("Delivered cost ÷ benchmark price ≤", "thr_cost_max", f'IF({S("avg_price")}>0,{S("avg_cpb")}/{S("avg_price")},1)', FMT_PCT, "<=", "Average delivered cost per saleable box vs achievable price"),
        ("Container length utilisation ≥", "thr_util_min", f'IF({S("ct")}=4,1,{S("lenutil")})', FMT_PCT, ">=", "LCL treated as 100%"),
        ("Buyer demand committed (share of shipment) ≥", "thr_demand_min", "demand_committed", FMT_PCT, ">=", "Written POs/LOIs before balance payment"),
        ("Unresolved shipment-blocking items ≤", "thr_blockers_max", 'COUNTIFS(rfq_blocks,"SHIPMENT",rfq_status,"<>Resolved")', "0", "<=", "From 'Quote Requests & Missing Data'"),
        ("Load physically fits", None, S("fits"), None, "=", "Geometry model"),
    ]
    rr += 2
    for lab, thr, act, fm, op, basis in tests:
        put(ws, rr, 1, lab)
        if thr:
            calc_cell(ws, rr, 2, "=" + thr, fm)
        else:
            put(ws, rr, 2, "TRUE")
        calc_cell(ws, rr, 3, "=" + act, fm)
        if op == ">=":
            calc_cell(ws, rr, 4, f'=IF(C{rr}>=B{rr},"PASS","FAIL")')
        elif op == "<=":
            calc_cell(ws, rr, 4, f'=IF(C{rr}<=B{rr},"PASS","FAIL")')
        else:
            calc_cell(ws, rr, 4, f'=IF(C{rr},"PASS","FAIL")')
        put(ws, rr, 7, basis, wrap=True)
        rr += 1
    ws.conditional_formatting.add("D49:D55", CellIsRule(operator="equal", formula=['"PASS"'], fill=FILL_OK))
    ws.conditional_formatting.add("D49:D55", CellIsRule(operator="equal", formula=['"FAIL"'], fill=FILL_BAD))
    rr += 1
    section(ws, rr, "Threshold inputs (provisional – no client targets supplied)", 7)
    rr += 1
    for lab, nm, v, fm in [("GO gross-margin threshold", "thr_gm_go", I.THRESHOLDS["gm_go"], FMT_PCT), ("CONDITIONAL gross-margin floor", "thr_gm_cond", I.THRESHOLDS["gm_conditional"], FMT_PCT),
                           ("Minimum contribution margin", "thr_cm_min", I.THRESHOLDS["cm_min"], FMT_PCT),
                           ("Maximum delivered cost ÷ benchmark price", "thr_cost_max", I.THRESHOLDS["cost_ratio_max"], FMT_PCT),
                           ("Minimum container utilisation", "thr_util_min", I.THRESHOLDS["util_min"], FMT_PCT),
                           ("Minimum committed buyer demand", "thr_demand_min", I.THRESHOLDS["demand_min"], FMT_PCT), ("Max unresolved shipment-blocking items", "thr_blockers_max", I.THRESHOLDS["compliance_blockers"], "0"),
                           ("Buyer demand committed today (share of shipment)", "demand_committed", 0.0, FMT_PCT)]:
        put(ws, rr, 1, lab)
        inp_cell(ws, rr, 2, v, fm)
        book.name(nm, ws.title, f"B{rr}")
        rr += 1
    rr += 1
    section(ws, rr, "Warnings", 7)
    rr += 1
    warns = [
        ("Supplier quotation validity", "=q_status"),
        ("Supplier price anomaly", "=q_anomaly"),
        ("Supplier identity", '="WARN – NFC identity, manufacturer status and bank beneficiary are UNVERIFIED (S088). No advance payment until verified."'),
        ("Decision-relevant inputs that are ASSUMED/UNRESOLVED/ESTIMATED", '="WARN – "&COUNTIFS(asm_flag,"⚠*")&" high-impact inputs are not verified (see Assumptions Register)"'),
        ("Model integrity checks", "=chk_overall"),
        ("Physical feasibility of selected case", f'=IF({S("fits")},"OK – fits (provisional geometry)","FAIL – selected configuration does not fit")'),
        ("Recommended equipment for quoted order", "=ship_reco"),
    ]
    for lab, f in warns:
        put(ws, rr, 1, lab, bold=True)
        calc_cell(ws, rr, 2, f)
        ws.merge_cells(start_row=rr, start_column=2, end_row=rr, end_column=7)
        rr += 1
    status_cf(ws, f"B{rr - len(warns)}:B{rr - 1}")
    rr += 1
    section(ws, rr, "Selected configuration & destination under LOW / BASE / STRESS", 7)
    header(ws, rr + 1, ["Metric", "LOW", "BASE", "STRESS"])
    rr += 2
    for lab, key, fm in [("Delivered cost per saleable box", "avg_cpb", FMT_USD4), ("Achievable price per box", "avg_price", FMT_USD4), ("Gross margin", "GM", FMT_PCT),
                         ("Contribution margin", "CM", FMT_PCT), ("Contribution (USD)", "CONTRIB", FMT_USD), ("Peak working capital", "PEAK", FMT_USD), ("Load fits?", "fits", None)]:
        put(ws, rr, 1, lab)
        for j in range(3):
            calc_cell(ws, rr, 2 + j, f"=INDEX(eng_{key},MATCH({j + 1}*1000+sel_cfg*10+sel_dest,eng_key,0))", fm)
        rr += 1
    rr += 1
    section(ws, rr, "Best options in the selected scenario (by contribution, physically feasible, selected destination)", 7)
    header(ws, rr + 1, ["Rank", "Configuration", "Contribution", "Contribution margin", "Delivered cost/box"])
    rr += 2
    for k in range(1, 6):
        put(ws, rr, 1, k)
        calc_cell(ws, rr, 2, f"=INDEX(scomp_cfgname,MATCH({k},scomp_rank,0))")
        calc_cell(ws, rr, 3, f"=INDEX(scomp_contrib,MATCH({k},scomp_rank,0))", FMT_USD)
        calc_cell(ws, rr, 4, f"=INDEX(scomp_cm,MATCH({k},scomp_rank,0))", FMT_PCT)
        calc_cell(ws, rr, 5, f"=INDEX(scomp_cpb,MATCH({k},scomp_rank,0))", FMT_USD4)
        rr += 1


def build_readme(book):
    ws = book.ws(SH["readme"])
    title(ws, "Read Me & Instructions", "How to use, audit and update the BigBoxPizza landed-cost model")
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 150
    lines = [
        ("PURPOSE", "Decision model for importing flat-packed corrugated pizza boxes from Nile Factory Carton (6th of October, Egypt) to wholesale customers on the US East Coast. It traces every cost from the factory gate to the customer's dock, compares delivered cost with evidence-based selling prices, and shows cash needs."),
        ("STATUS", "PROVISIONAL. The NFC quotation expired on 30-Sep-2026; no freight, broker, trucking or buyer quotations were available; NFC technical data and bundle geometry are missing. Results are model outputs, NOT actual expenses."),
        ("HOW TO USE", "1) On 'Executive Dashboard' choose Scenario (1 LOW, 2 BASE, 3 STRESS), Configuration (1–10) and Destination (1–5). 2) Read the KPI block, threshold tests and warnings. 3) Use 'Scenario Comparison', 'Container Profitability' and 'Sensitivity Analysis' for options."),
        ("COLOUR CODE", "Yellow fill + blue font = editable input. Grey fill = formula (do not overwrite). Orange fill = value written by a script (geometry optimiser / DP validation / market snapshot). Green/amber/red = evidence status or check result."),
        ("INPUTS", "Inputs live on the input sheets (Supplier Quotation, Technical Specifications, Exchange Rates, Container Specifications, Origin Costs, Ocean Freight, U.S. Port & Customs, Tariffs & Customs Value, Destination Delivery, Pricing & Margin, Competitor Benchmark). Each has LOW/BASE/STRESS columns, evidence class and source IDs."),
        ("EVIDENCE CLASSES", "VERIFIED_OFFICIAL, VERIFIED_QUOTE, VERIFIED_SUPPLIER, VERIFIED_MARKET, CALCULATED, ESTIMATED, ASSUMED, UNRESOLVED (brief §3.4). A formula result is never 'verified' just because it calculates."),
        ("CALC ENGINE", "'Calc Engine' holds one row per scenario × configuration × destination (150 rows) plus sensitivity (33) and combination (6) rows. All views read from it by INDEX/MATCH. 'Model Checks' reconciles the engine with the detailed ledger on 'Landed Cost by SKU'."),
        ("ALLOCATION", "Supplier price, VAT, duty: direct by SKU. MPF/HMF: by customs value. Insurance: by supplier value. Container-driven costs (origin per container, ocean, US per-container, drayage, unloading): by cube (bundle volume). Per-shipment admin (origin docs, broker, ISF, bonds, DO): by units."),
        ("GEOMETRY", "Blank and bundle sizes are ESTIMATED from a calibrated die-line rule (length = 2L + 4.5H, width = W + 2H + 13 mm; 50 blanks/bundle; 1.6 mm pitch BASE). Floor patterns are formulas; an exhaustive guillotine DP in scripts/loading_model.py validates them (orange column). The equal-mix maxima (orange) come from the script; if you change geometry inputs, re-run scripts/build_all.py – the FITS columns re-test the values automatically."),
        ("DEFINITIONS", "Gross margin = (price − COGS)/price. Markup = (price − COGS)/COGS. Contribution = gross profit − commission − payment processing − bad debt − samples/testing − sales admin − financing cost. COGS = customer-delivered economic cost (recoverable VAT excluded)."),
        ("TAX VIEWS", "VAT mode 1 = zero-rated direct export (no VAT); mode 2 = VAT paid and refunded (cash only; financing cost); mode 3 = VAT paid and not recoverable (economic cost, and added to customs value). Selected by scenario or by sensitivity rows."),
        ("CUSTOMS VALUE", "Customs value = EXW/FCA price (+ non-recoverable VAT in mode 3, + tooling). Egyptian inland freight is not added for proven ex-factory sales (19 CFR 152.103(a)(5)); international freight and insurance are excluded. Duty = MFN (Free) + Section 301 Egypt 12.5% (BASE)."),
        ("RECALCULATION", "The delivered file was recalculated with LibreOffice 24.2 (headless) and re-opened programmatically; values were compared with the independent Python engine (scripts/engine.py). Excel recalculates on open (fullCalcOnLoad)."),
        ("REBUILD", "python3 BigBoxPizza/scripts/build_all.py  – rebuilds geometry diagrams, workbook, recalculation, validation, CSV source register and Markdown deliverables."),
        ("IMPORTER OF RECORD", "Options: BigBoxPizza as foreign IOR (CBP-assigned number, bond, broker POA); new US entity; third-party IOR service; or sell FCA/FOB to a US distributor who imports. A customs broker does not assume the IOR's legal obligations. See 'U.S. Port & Customs' §5."),
        ("LIMITATIONS", "Direct access to official websites was blocked in the research environment; sources were read via search-engine extracts (see Source Register). Re-verify all VERIFIED_OFFICIAL items on the live sites before shipment. Not legal or tax advice."),
    ]
    r = 4
    for h, t in lines:
        put(ws, r, 2, h, bold=True, border=False)
        r += 1
        put(ws, r, 2, t, wrap=True, border=False)
        ws.row_dimensions[r].height = 46
        r += 2
    put(ws, r, 2, "SHEET MAP", bold=True, border=False)
    r += 1
    for k in ["dash", "readme", "sku", "quote", "spec", "fx", "cont", "geo", "ship", "orig", "ocean", "usc", "dest", "tariff", "landed", "price", "prof",
              "sens", "scen", "cash", "comp", "risk", "assum", "src", "rfq", "eng", "chk"]:
        put(ws, r, 2, "• " + SH[k], border=False)
        r += 1


# =============================================================================== landed cost ledger
LEDGER = [
    # id, category, description, payer, trigger, currency, unit basis, rate expr (active), alloc, sources, evidence, confidence, recoverable, timing, cash formula, econ formula, notes
    ("O-01", "Supplier", "Product price (EXW/FCA), all SKUs", "BigBoxPizza", "PO", "EGP→USD", "per box", "q_price × (1+re-quote)", "Direct by SKU", "S001", "VERIFIED_QUOTE", "Medium", "No", "50% at PO, 50% before collection", S("SUP"), S("SUP"), "Quote expired 30-Sep-2026; re-quote required"),
    ("O-02", "Tax", "Egyptian VAT 14% on supplier invoice (if charged)", "BigBoxPizza / Egyptian exporter", "Invoice", "EGP→USD", "% of invoice", "14% × invoice (mode 2/3)", "Direct by SKU", "S001;S060", "UNRESOLVED", "Medium", "Mode 2: refundable (cash only)", "With supplier payments", S("VAT_CASH"), S("VAT_ECON"), "Economic cost only in mode 3"),
    ("O-03", "Supplier", "Tooling / dies / plates", "BigBoxPizza", "PO", "EGP→USD", "one-off", "INDEX(in_sup_tooling_egp)", "By units", "", "ASSUMED", "Low", "No", "At PO", S("tooling"), S("tooling"), ""),
    ("O-04", "Origin", "Inland trucking factory → Alexandria/Dekheila (or CFS for LCL)", "BigBoxPizza", "Collection", "EGP→USD", "per container", "truck_20/40", "By cube", "S066;S067;S068", "ESTIMATED", "Low", "No", "At export",
     f"IF({S('ct')}=4,INDEX(in_ori_lcl_truck,1,sel_scen),{S('n')}*IF({S('ct')}=1,INDEX(in_ori_truck_20,1,sel_scen),INDEX(in_ori_truck_40,1,sel_scen)))/{S('fx')}", None, ""),
    ("O-05", "Origin", "Terminal receiving + VGM weighing", "BigBoxPizza", "Gate-in", "USD (paid EGP)", "per container", "terminal", "By cube", "S069", "VERIFIED_MARKET", "Medium", "No", "At export", f"IF({S('ct')}=4,0,{S('n')}*INDEX(in_ori_terminal,1,sel_scen))", None, ""),
    ("O-06", "Origin", "Origin THC (if not in freight)", "BigBoxPizza", "Loading", "USD", "per container", "othc_20/40", "By cube", "S050", "VERIFIED_MARKET", "Medium", "No", "At export",
     f"IF({S('ct')}=4,0,{S('n')}*IF({S('ct')}=1,INDEX(in_ori_othc_20,1,sel_scen),INDEX(in_ori_othc_40,1,sel_scen))*(1-INDEX(in_ori_othc_in_freight,1,sel_scen)))", None, "Double-count flag on Origin Costs"),
    ("O-07", "Origin", "Container seal", "BigBoxPizza", "Loading", "USD", "per container", "seal", "By cube", "", "ASSUMED", "Low", "No", "At export", f"IF({S('ct')}=4,0,{S('n')}*INDEX(in_ori_seal,1,sel_scen))", None, ""),
    ("O-08", "Origin", "Egyptian export inspection (if selected)", "BigBoxPizza", "Inspection", "USD", "per container", "inspection", "By cube", "S069", "VERIFIED_MARKET", "Low", "No", "At export", f"IF({S('ct')}=4,0,{S('n')}*INDEX(in_ori_inspection,1,sel_scen))", None, "STRESS only"),
    ("O-09", "Origin", "Origin detention beyond free time", "BigBoxPizza", "Delay", "USD", "per container-day", "dd_days × rate", "By cube", "S070", "VERIFIED_MARKET", "Low", "No", "At export",
     f"IF({S('ct')}=4,0,{S('n')}*INDEX(in_ori_dd_days,1,sel_scen)*IF({S('ct')}=1,INDEX(in_ori_dd_20,1,sel_scen),INDEX(in_ori_dd_40,1,sel_scen)))", None, "STRESS only"),
    ("O-10", "Origin", "Factory loading labour (if NFC charges under EXW)", "BigBoxPizza", "Loading", "EGP→USD", "per container", "loading_egp", "By cube", "S072", "ASSUMED", "Low", "No", "At export", f"IF({S('ct')}=4,0,{S('n')}*INDEX(in_ori_loading_egp,1,sel_scen)/{S('fx')})", None, "STRESS only"),
    ("O-11", "Origin", "LCL origin fixed charges (documents, CFS)", "BigBoxPizza", "CFS", "USD", "per shipment", "lcl_cfs_o", "By cube", "", "ASSUMED", "Low", "No", "At export", f"IF({S('ct')}=4,INDEX(in_ori_lcl_cfs_o,1,sel_scen),0)", None, "LCL only"),
    ("O-12", "Origin", "Export customs clearance & documentation", "BigBoxPizza", "Export", "EGP→USD", "per shipment", "clearance", "By units", "S062", "ASSUMED", "Low", "No", "At export", f"INDEX(in_ori_clearance,1,sel_scen)/{S('fx')}", None, ""),
    ("O-13", "Origin", "Certificate of origin (optional)", "BigBoxPizza", "Export", "EGP→USD", "per shipment", "coo", "By units", "", "ASSUMED", "Low", "No", "At export", f"INDEX(in_ori_coo,1,sel_scen)/{S('fx')}", None, ""),
    ("O-14", "Origin", "B/L & carrier documentation", "BigBoxPizza", "B/L", "USD", "per shipment", "bl_fee", "By units", "S050", "ASSUMED", "Low", "No", "At export", "INDEX(in_ori_bl_fee,1,sel_scen)", None, ""),
    ("O-15", "Origin", "Forwarder origin handling", "BigBoxPizza", "Booking", "USD", "per shipment", "fwd_fee", "By units", "", "ASSUMED", "Low", "No", "At export", "INDEX(in_ori_fwd_fee,1,sel_scen)", None, ""),
    ("O-16", "Origin", "Pre-shipment QC inspection", "BigBoxPizza", "Before loading", "USD", "per shipment", "qc", "By units", "", "ASSUMED", "Low", "No", "At export", "INDEX(in_ori_qc,1,sel_scen)", None, ""),
    ("O-17", "Origin", "Bank wire charges", "BigBoxPizza", "Payments", "USD", "per wire", "wires × fee", "By units", "", "ASSUMED", "Low", "No", "At payments", "INDEX(in_ori_wires,1,sel_scen)*INDEX(in_ori_wire_fee,1,sel_scen)", None, ""),
    ("F-01", "Ocean", "Ocean freight incl. BAF & destination THC (container), or LCL all-in W/M incl. CFS handling", "BigBoxPizza", "Booking", "USD", "per container", "INDEX(tbl_ocean_rate) + port diff", "By cube", "S044-S049", "ESTIMATED", "Medium-Low", "No", "Prepaid at export", S("ocean_ctr"), None, ""),
    ("F-02", "Ocean", "AMS / manifest filing", "BigBoxPizza", "Booking", "USD", "per B/L", "ams", "By cube", "", "ASSUMED", "Low", "No", "At export", "INDEX(in_oce_ams,1,sel_scen)", None, ""),
    ("F-03", "Insurance", "Cargo insurance ICC(A), (CIF+10%) × rate, min premium", "BigBoxPizza", "Shipment", "USD", "% insured value", "ins_rate", "By supplier value", "S089", "ESTIMATED", "Medium-Low", "No", "At export", S("INS"), None, "Double-count flag on Ocean Freight"),
    ("U-01", "Duty", "MFN duty HTS 4819.10.00 (Free)", "IOR", "Entry", "USD", "% customs value", "0%", "Direct (customs value)", "S010;S011", "VERIFIED_OFFICIAL", "High", "No", "Before release", f"{S('CV')}*INDEX(in_cus_mfn,1,sel_scen)", None, ""),
    ("U-02", "Duty", "Section 301 forced-labor duty, Egypt (9903.05.36)", "IOR", "Entry", "USD", "% customs value", "12.5% BASE", "Direct (customs value)", "S014;S015;S016", "VERIFIED_OFFICIAL", "Medium (coverage)", "No (refund only if invalidated)", "Before release", f"{S('CV')}*{S('s301')}", None, ""),
    ("U-03", "Gov. fee", "Merchandise Processing Fee (0.3464%, min/max FY2027)", "IOR", "Entry", "USD", "% value, min/max", "0.3464%", "By customs value", "S024", "VERIFIED_OFFICIAL", "High", "No", "Before release", S("MPF"), None, "Not bundled in brokerage"),
    ("U-04", "Gov. fee", "Harbor Maintenance Fee (0.125%)", "IOR", "Entry", "USD", "% value", "0.125%", "By customs value", "S025", "VERIFIED_OFFICIAL", "High", "No", "Before release", S("HMF"), None, ""),
    ("U-05", "Customs", "Customs broker entry fee", "IOR", "Entry", "USD", "per entry", "broker", "By units", "S039", "ESTIMATED", "Medium-Low", "No", "Before release", "INDEX(in_cus_broker,1,sel_scen)", None, ""),
    ("U-06", "Customs", "ISF 10+2 filing", "IOR", "Pre-loading", "USD", "per shipment", "isf", "By units", "S037;S039", "ESTIMATED", "Medium-Low", "No", "Before loading", "INDEX(in_cus_isf,1,sel_scen)", None, ""),
    ("U-07", "Customs", "Single-transaction customs bond", "IOR", "Entry", "USD", "per $1,000 face", "stb_rate, min", "By units", "S038", "ESTIMATED", "Medium-Low", "No", "Before release", S("STB"), None, ""),
    ("U-08", "Customs", "ISF bond", "IOR", "Pre-loading", "USD", "per shipment", "isf_bond", "By units", "S038", "ASSUMED", "Low", "No", "Before loading", "INDEX(in_cus_isf_bond,1,sel_scen)", None, ""),
    ("U-09", "Port", "Delivery order / arrival handling", "IOR", "Arrival", "USD", "per shipment", "do_fee", "By units", "", "ASSUMED", "Low", "No", "Before release", "INDEX(in_cus_do_fee,1,sel_scen)", None, ""),
    ("U-10", "Port", "PANYNJ Cargo Facility Charge (NY/NJ only)", "IOR / carrier", "Discharge", "USD", "per loaded TEU", "14.80", "By cube", "S056", "VERIFIED_OFFICIAL", "High", "No", "Before release", S("CFC"), None, "Double-count flag (often in freight)"),
    ("U-11", "Disruption", "CBP exam + exam-site drayage", "IOR", "Exam", "USD", "per container", "exam + exam_dray", "By cube", "S091", "ESTIMATED", "Medium-Low", "No", "Before release", S("EXAM"), None, "STRESS only"),
    ("U-12", "Disruption", "Demurrage / storage beyond free time", "IOR", "Delay", "USD", "per container-day", "dem_days × dem_rate", "By cube", "S057", "ESTIMATED", "Low", "No", "Before release", S("DEM"), None, "STRESS only"),
    ("D-01", "Delivery", "Drayage linehaul incl. fuel surcharge (or LCL destination fixed charges + final delivery)", "BigBoxPizza", "Delivery", "USD", "per container", "line × (1+FSC)", "By cube", "S052;S053;S094", "ESTIMATED", "Low", "No", "At delivery",
     f"IF({S('ct')}=4,INDEX(in_dra_lcl_cfs_d,1,sel_scen)+INDEX(in_dra_lcl_deliv,1,sel_scen),{S('n')}*INDEX(tbl_dest_line,sel_dest,sel_scen)*(1+INDEX(in_dra_fsc,1,sel_scen)))", None, ""),
    ("D-02", "Delivery", "Tolls", "BigBoxPizza", "Delivery", "USD", "per container", "tolls", "By cube", "", "ASSUMED", "Low", "No", "At delivery", f"IF({S('ct')}=4,0,{S('n')}*INDEX(tbl_dest_tolls,sel_dest,sel_scen))", None, ""),
    ("D-03", "Delivery", "Chassis rental (if not in linehaul)", "BigBoxPizza", "Delivery", "USD", "per container-day", "days × rate", "By cube", "S054", "ESTIMATED", "Low", "No", "At delivery",
     f"IF({S('ct')}=4,0,{S('n')}*INDEX(in_dra_chassis_days,1,sel_scen)*INDEX(tbl_dest_chassis,sel_dest,sel_scen)*(1-INDEX(in_dra_chassis_in_dray,1,sel_scen)))", None, "Double-count flag"),
    ("D-04", "Delivery", "Waiting time beyond 2 free hours", "BigBoxPizza", "Live unload", "USD", "per hour", "hours × rate", "By cube", "", "ASSUMED", "Low", "No", "At delivery", f"IF({S('ct')}=4,0,{S('n')}*INDEX(in_dra_wait_hours,1,sel_scen)*INDEX(in_dra_wait_rate,1,sel_scen))", None, ""),
    ("D-05", "Delivery", "Chassis split", "BigBoxPizza", "Delivery", "USD", "per container", "split", "By cube", "S052", "ESTIMATED", "Low", "No", "At delivery", f"IF({S('ct')}=4,0,{S('n')}*INDEX(in_dra_split,1,sel_scen))", None, "STRESS only"),
    ("D-06", "Disruption", "Pre-pull + yard storage", "BigBoxPizza", "Delay", "USD", "per container", "prepull", "By cube", "", "ASSUMED", "Low", "No", "At delivery", f"IF({S('ct')}=4,0,{S('n')}*INDEX(in_dra_prepull,1,sel_scen))", None, "STRESS only"),
    ("D-07", "Disruption", "Dry run / failed delivery", "BigBoxPizza", "Failed delivery", "USD", "per container", "dryrun", "By cube", "", "ASSUMED", "Low", "No", "At delivery", f"IF({S('ct')}=4,0,{S('n')}*INDEX(in_dra_dryrun,1,sel_scen))", None, "STRESS only"),
    ("D-08", "Delivery", "Unloading floor-loaded container (if not in dray quote)", "BigBoxPizza", "Delivery", "USD", "per container", "unload_20/40", "By cube", "S055", "ESTIMATED", "Low", "No", "At delivery", S("UNLOAD"), None, "Double-count flag"),
]


def build_landed(book):
    ws = book.ws(SH["landed"])
    title(ws, "Landed Cost by SKU – cost ledger, allocation and value ladder (selected case)",
          "Selected on the Dashboard. Every cost line appears once; recoverable taxes are shown as cash but excluded from economic cost unless non-recoverable.")
    widths = {"A": 7, "B": 11, "C": 46, "D": 14, "E": 11, "F": 10, "G": 13, "H": 18, "I": 15, "J": 14, "K": 18, "L": 10, "M": 16, "N": 14, "O": 14, "P": 14, "Q": 8, "R": 30}
    set_widths(ws, widths)
    put(ws, 3, 1, "Case:", bold=True, border=False)
    calc_cell(ws, 3, 3, '=CHOOSE(sel_scen,"LOW","BASE","STRESS")&" | "&INDEX(cfg_name,sel_cfg)&" | "&INDEX(dest_gw,sel_dest)&" → "&INDEX(dest_name,sel_dest)')
    ws.merge_cells("C3:R3")
    r = section(ws, 5, "1. Cost ledger (brief §13.1 fields)", 18)
    r = header(ws, r, ["ID", "Category", "Description", "Payer", "Trigger", "Currency", "Unit basis", "Rate / formula basis", "Allocation", "Source IDs", "Evidence",
                       "Confidence", "Recoverable?", "Payment timing", "CASH amount USD", "ECONOMIC cost USD", "Include", "Notes"])
    first = r
    for row in LEDGER:
        (lid, cat, desc, payer, trig, cur, ub, rate, alloc, src, ev, conf, rec, timing, fcash, fecon, note) = row
        vals = [lid, cat, desc, payer, trig, cur, ub, rate, alloc, src, ev, conf, rec, timing]
        for j, v in enumerate(vals):
            put(ws, r, 1 + j, v, wrap=(j in (2, 7, 12, 13)))
        calc_cell(ws, r, 15, "=" + fcash, FMT_USD)
        calc_cell(ws, r, 16, "=" + (fecon if fecon else f"O{r}"), FMT_USD)
        inp_cell(ws, r, 17, 1, "0")
        put(ws, r, 18, note, wrap=True)
        ws.row_dimensions[r].height = 30
        r += 1
    last = r - 1
    evidence_cf(ws, f"K{first}:K{last}")
    book.name("led_ids", ws.title, f"A{first}:A{last}")
    book.name("led_cat", ws.title, f"B{first}:B{last}")
    book.name("led_cash", ws.title, f"O{first}:O{last}")
    book.name("led_econ", ws.title, f"P{first}:P{last}")
    book.name("led_incl", ws.title, f"Q{first}:Q{last}")
    put(ws, r, 3, "TOTAL (included lines)", bold=True)
    calc_cell(ws, r, 15, f"=SUMPRODUCT(O{first}:O{last},Q{first}:Q{last})", FMT_USD, bold=True)
    calc_cell(ws, r, 16, f"=SUMPRODUCT(P{first}:P{last},Q{first}:Q{last})", FMT_USD, bold=True)
    book.name("led_total_econ", ws.title, f"P{r}")
    book.name("led_total_cash", ws.title, f"O{r}")
    r += 1
    put(ws, r, 3, "Engine COGS (must equal economic total)", bold=True)
    calc_cell(ws, r, 16, "=" + S("COGS"), FMT_USD)
    calc_cell(ws, r, 17, f'=IF(ABS(P{r}-P{r - 1})<0.01,"OK","FAIL")')
    book.name("led_chk_cogs", ws.title, f"Q{r}")
    r += 1
    put(ws, r, 3, "Duplicate cost IDs in ledger (must be 0)", bold=True)
    calc_cell(ws, r, 16, f"=SUMPRODUCT((COUNTIF(A{first}:A{last},A{first}:A{last})>1)*1)", "0")
    calc_cell(ws, r, 17, f'=IF(P{r}=0,"OK","FAIL")')
    book.name("led_chk_dup", ws.title, f"Q{r}")
    r += 1
    for cat_label, cats, eng_expr in [("Origin subtotal = engine ORIGIN", ["Origin"], S("ORIGIN")),
                                      ("Ocean + insurance = engine OCEAN + INS", ["Ocean", "Insurance"], f"{S('OCEAN')}+{S('INS')}"),
                                      ("US duty/fees/port/disruption = engine", ["Duty", "Gov. fee", "Customs", "Port"], f"{S('DUTY')}+{S('MPF')}+{S('HMF')}+{S('US_SHP')}+{S('CFC')}"),
                                      ("Delivery + disruption(D) = engine DELIV + UNLOAD + EXAM + DEM", ["Delivery", "Disruption"], f"{S('DELIV')}+{S('UNLOAD')}+{S('EXAM')}+{S('DEM')}")]:
        put(ws, r, 3, cat_label, bold=True)
        sumexpr = "+".join([f'SUMIFS(P{first}:P{last},B{first}:B{last},"{c}")' for c in cats])
        calc_cell(ws, r, 15, "=" + eng_expr, FMT_USD)
        calc_cell(ws, r, 16, "=" + sumexpr, FMT_USD)
        calc_cell(ws, r, 17, f'=IF(ABS(P{r}-O{r})<0.01,"OK","FAIL")')
        book.name(f"led_chk_{cats[0].replace('.', '').replace(' ', '').lower()}", ws.title, f"Q{r}")
        r += 1
    status_cf(ws, f"Q{r - 6}:Q{r - 1}")
    r += 1
    # ---------------- allocation by SKU
    r = section(ws, r, "2. Allocation by SKU and delivered cost per saleable box", 18)
    r = header(ws, r, ["", "", "Cost group", "Allocation basis", "3464", "3463", "3460", "TOTAL", "Engine", "Check"])
    groups = [
        ("Supplier price", "Direct", [S(f"sup_{c}") for c in SKU_CODES], S("SUP")),
        ("VAT – economic (mode 3 only)", "Direct", [f"IF({S('vatmode')}=3,{S('sup_' + c)}*INDEX(in_sup_vat_rate,1,sel_scen),0)" for c in SKU_CODES], S("VAT_ECON")),
        ("Tooling", "Units", [f"{S('tooling')}*{S('units_' + c)}/{S('U')}" for c in SKU_CODES], S("tooling")),
        ("Duty (MFN + §301)", "Direct (customs value)", [f"{S('cv_' + c)}*{S('duty_rate')}" for c in SKU_CODES], S("DUTY")),
        ("MPF + HMF", "Customs value", [f"({S('MPF')}+{S('HMF')})*{S('cv_' + c)}/{S('CV')}" for c in SKU_CODES], f"{S('MPF')}+{S('HMF')}"),
        ("Insurance", "Supplier value", [f"{S('INS')}*{S('sup_' + c)}/{S('SUP')}" for c in SKU_CODES], S("INS")),
        ("Container-driven: origin/ctr, ocean, US/ctr, delivery, unloading", "Cube", [f"{S('shared_space')}*{S('vol_' + c)}/{S('V')}" for c in SKU_CODES], S("shared_space")),
        ("Per-shipment admin: origin docs, broker, ISF, bonds, DO", "Units", [f"{S('shared_admin')}*{S('units_' + c)}/{S('U')}" for c in SKU_CODES], S("shared_admin")),
    ]
    g0 = r
    for lab, basis, fs, ef in groups:
        put(ws, r, 3, lab, wrap=True)
        put(ws, r, 4, basis)
        for j, f in enumerate(fs):
            calc_cell(ws, r, 5 + j, "=" + f, FMT_USD)
        calc_cell(ws, r, 8, f"=SUM(E{r}:G{r})", FMT_USD)
        calc_cell(ws, r, 9, "=" + ef, FMT_USD)
        calc_cell(ws, r, 10, f'=IF(ABS(H{r}-I{r})<0.01,"OK","FAIL")')
        r += 1
    put(ws, r, 3, "TOTAL DELIVERED COST (economic)", bold=True)
    for j in range(4):
        calc_cell(ws, r, 5 + j, f"=SUM({col(5 + j)}{g0}:{col(5 + j)}{r - 1})", FMT_USD, bold=True)
    calc_cell(ws, r, 9, "=" + S("COGS"), FMT_USD)
    calc_cell(ws, r, 10, f'=IF(ABS(H{r}-I{r})<0.01,"OK","FAIL")')
    book.name("led_chk_alloc", ws.title, f"J{r}")
    tot_r = r
    status_cf(ws, f"J{g0}:J{r}")
    r += 1
    for lab, fs, fm in [("Units shipped", [S(f"units_{c}") for c in SKU_CODES], FMT_INT), ("Saleable units", [S(f"sale_{c}") for c in SKU_CODES], FMT_INT)]:
        put(ws, r, 3, lab)
        for j, f in enumerate(fs):
            calc_cell(ws, r, 5 + j, "=" + f, fm)
        calc_cell(ws, r, 8, f"=SUM(E{r}:G{r})", fm)
        r += 1
    sale_r = r - 1
    for lab, fexpr, fm in [("Delivered cost per saleable box (USD)", lambda cl: f"=IF({cl}{sale_r}>0,{cl}{tot_r}/{cl}{sale_r},0)", FMT_USD4),
                           ("Delivered cost per 1,000 boxes (USD)", lambda cl: f"=IF({cl}{sale_r}>0,{cl}{tot_r}/{cl}{sale_r}*1000,0)", FMT_USD),
                           ("Delivered cost per box (EGP at scenario FX)", lambda cl: f"=IF({cl}{sale_r}>0,{cl}{tot_r}/{cl}{sale_r}*{S('fx')},0)", FMT_NUM3),
                           ("Supplier price per box (USD)", lambda cl: f"=IF({cl}{sale_r - 1}>0,{cl}{g0}/{cl}{sale_r - 1},0)", FMT_USD4),
                           ("Achievable wholesale price (USD)", None, FMT_USD4)]:
        put(ws, r, 3, lab, bold="saleable" in lab)
        for j, cl in enumerate(["E", "F", "G", "H"]):
            if fexpr:
                calc_cell(ws, r, 5 + j, fexpr(cl), fm, bold="saleable" in lab)
            elif j < 3:
                calc_cell(ws, r, 5 + j, "=" + S(f"price_{SKU_CODES[j]}"), fm)
            else:
                calc_cell(ws, r, 5 + j, "=" + S("avg_price"), fm)
        r += 1
    r += 1
    # ---------------- value ladder
    r = section(ws, r, "3. Value ladder – the eight measures are NOT interchangeable (brief §13.4)", 18)
    r = header(ws, r, ["", "#", "Measure", "Composition", "USD", "Per saleable box", "EGP"])
    ladder = [
        ("1", "Supplier invoice value (excl. VAT)", "Σ units × EGP price × (1+re-quote) / FX", S("SUP")),
        ("1b", "Supplier invoice incl. VAT (cash, if charged)", "(1) + VAT cash", f"{S('SUP')}+{S('VAT_CASH')}"),
        ("2", "Customs value", "(1) + non-recoverable VAT + tooling", S("CV")),
        ("3", "Dutiable value × duty = duty", "Customs value × (MFN + §301)", S("DUTY")),
        ("4", "Port-arrival cost", "(1) + econ. VAT + tooling + origin + ocean + insurance", f"{S('SUP')}+{S('VAT_ECON')}+{S('tooling')}+{S('ORIGIN')}+{S('OCEAN')}+{S('INS')}"),
        ("5", "Cleared-port cost", "(4) + duty + MPF + HMF + broker/ISF/bonds/DO + CFC + exam + demurrage", f"{S('COGS')}-{S('DELIV')}-{S('UNLOAD')}"),
        ("6", "Customer-delivered cost (COGS)", "(5) + drayage + accessorials + unloading", S("COGS")),
        ("7", "Fully burdened economic cost", "(6) + commission, processing, bad debt, testing, admin, financing", f"{S('COGS')}+{S('SELL_VAR')}+{S('SELL_FIX')}+{S('FIN')}"),
        ("8", "Total transaction cash needed", "All outflows incl. recoverable VAT (peak WC shown on Cash sheet)", S("CASH_TOTAL")),
    ]
    for num, lab, comp, f in ladder:
        put(ws, r, 2, num)
        put(ws, r, 3, lab, bold=True)
        put(ws, r, 4, comp, wrap=True)
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=4)
        calc_cell(ws, r, 5, "=" + f, FMT_USD, bold=True)
        calc_cell(ws, r, 6, f"=E{r}/{S('SALE')}", FMT_USD4)
        calc_cell(ws, r, 7, f"=E{r}*{S('fx')}", FMT_NUM)
        ws.row_dimensions[r].height = 30
        r += 1
    r += 1
    r = section(ws, r, "4. Reconciliation: supplier quotation → shipment value (formula)", 18)
    for lab, f, fm in [("Quoted subtotal EGP (printed)", "=q_subtotal", FMT_NUM),
                       ("Quoted units", "=q_qty_total", FMT_INT),
                       ("Selected-case units", "=" + S("U"), FMT_INT),
                       ("Selected-case supplier value EGP = Σ units × price × (1+re-quote) × supplier factor", f"={S('SUP')}*{S('fx')}", FMT_NUM),
                       ("… equals quoted subtotal × (1+re-quote) when units = quoted mix?", f'=IF(AND(INDEX(cfg_u_3464,sel_cfg,sel_scen)=q_qty_3464,INDEX(cfg_u_3463,sel_cfg,sel_scen)=q_qty_3463,INDEX(cfg_u_3460,sel_cfg,sel_scen)=q_qty_3460),IF(ABS({S("SUP")}*{S("fx")}-q_subtotal*(1+INDEX(in_sup_requote,1,sel_scen)))<0.01,"OK – reconciles","FAIL"),"n/a – configuration differs from quoted mix")', None)]:
        put(ws, r, 3, lab, wrap=True)
        calc_cell(ws, r, 5, f, fm)
        if "equals" in lab:
            book.name("led_chk_recon", ws.title, f"E{r}")
        r += 1


# =============================================================================== pricing & margin
def build_pricing(book):
    ws = book.ws(SH["price"])
    title(ws, "Pricing & Margin – required selling prices vs achievable benchmark (selected case)",
          "Gross margin = (P − COGS)/P. Markup = (P − COGS)/COGS. Contribution margin also deducts selling costs and financing.")
    set_widths(ws, {"A": 9, "B": 50, "C": 12, "D": 13, "E": 13, "F": 13, "G": 14, "H": 18, "I": 14, "J": 60})
    r = section(ws, 4, "1. Selling-cost and finance inputs", 10)
    rows, r = input_table(book, ws, r, "sel", list(I.SELLING.items()), "SEL")
    r += 1
    r = section(ws, r, "2. Margin at benchmark price (selected case)", 10)
    r = header(ws, r, ["", "Measure", "", "3464", "3463", "3460", "Average"])
    base_rows = {}
    for lab, fs, avg, fm in [
        ("Delivered cost per saleable box (COGS)", [S(f"cpb_{c}") for c in SKU_CODES], S("avg_cpb"), FMT_USD4),
        ("Achievable wholesale price (benchmark)", [S(f"price_{c}") for c in SKU_CODES], S("avg_price"), FMT_USD4),
        ("Gross margin at benchmark", None, S("GM"), FMT_PCT),
        ("Markup at benchmark", None, None, FMT_PCT),
        ("Headroom = benchmark − cost (USD/box)", None, None, FMT_USD4),
    ]:
        put(ws, r, 2, lab)
        base_rows[lab] = r
        for j in range(3):
            cl = col(4 + j)
            if fs:
                calc_cell(ws, r, 4 + j, "=" + fs[j], fm)
            elif lab.startswith("Gross"):
                calc_cell(ws, r, 4 + j, f"=IF({cl}{r - 1}>0,({cl}{r - 1}-{cl}{r - 2})/{cl}{r - 1},0)", fm)
            elif lab.startswith("Markup"):
                calc_cell(ws, r, 4 + j, f"=IF({cl}{r - 3}>0,({cl}{r - 2}-{cl}{r - 3})/{cl}{r - 3},0)", fm)
            else:
                calc_cell(ws, r, 4 + j, f"={cl}{r - 3}-{cl}{r - 4}", fm)
        if avg:
            calc_cell(ws, r, 7, "=" + avg, fm, bold=True)
        elif lab.startswith("Markup"):
            calc_cell(ws, r, 7, f"=IF(G{r - 3}>0,(G{r - 2}-G{r - 3})/G{r - 3},0)", fm)
        else:
            calc_cell(ws, r, 7, f"=G{r - 3}-G{r - 4}", fm)
        r += 1
    cost_r = base_rows["Delivered cost per saleable box (COGS)"]
    price_r = base_rows["Achievable wholesale price (benchmark)"]
    r += 1
    r = section(ws, r, "3. Selling price required for target gross margin = COGS / (1 − GM)", 10)
    r = header(ws, r, ["", "Target GM", "", "3464", "3463", "3460", "Average", "vs benchmark (avg)"])
    for gm in I.GM_TARGETS:
        put(ws, r, 2, "Gross margin")
        inp_cell(ws, r, 3, gm, FMT_PCT)
        for j in range(4):
            cl = col(4 + j)
            calc_cell(ws, r, 4 + j, f"={cl}{cost_r}/(1-$C{r})", FMT_USD4)
        calc_cell(ws, r, 8, f"=G{r}/G{price_r}-1", "+0.0%;-0.0%")
        r += 1
    r += 1
    r = section(ws, r, "4. Selling price required for target CONTRIBUTION margin = (COGS + fixed selling/box + financing/box) / (1 − variable selling % − CM)", 10)
    r = header(ws, r, ["", "Target CM", "", "3464", "3463", "3460", "Average"])
    fixed_box = f"(({S('SELL_FIX')}+{S('FIN')})/{S('SALE')})"
    for cm in (0.0, 0.05, 0.10, 0.15, 0.20):
        put(ws, r, 2, "Contribution margin")
        inp_cell(ws, r, 3, cm, FMT_PCT)
        for j in range(4):
            cl = col(4 + j)
            calc_cell(ws, r, 4 + j, f"=({cl}{cost_r}+{fixed_box})/(1-{S('var_pct')}-$C{r})", FMT_USD4)
        r += 1
    r += 1
    r = section(ws, r, "5. Maximum NFC unit price (EGP, quote basis) that still gives the target GM at the benchmark price (linearised)", 10)
    r = header(ws, r, ["", "Target GM", "", "3464", "3463", "3460", "", "Quoted price"])
    for gm in I.GM_TARGETS + [0.0]:
        put(ws, r, 2, "Gross margin")
        inp_cell(ws, r, 3, gm, FMT_PCT)
        for j, c in enumerate(SKU_CODES):
            f = (f"=IF({S('units_' + c)}>0,({S('price_' + c)}*(1-$C{r})*(1-{S('dmg')})-{S('o_' + c)})/(1+{S('a_' + c)})*{S('fx')}/((1+{S('req')})*{S('supfac')}),\"\")")
            calc_cell(ws, r, 4 + j, f, FMT_NUM3)
        put(ws, r, 8, "8.365 / 7.900 / 6.900")
        r += 1
    put(ws, r, 2, "Negative values mean no positive EXW price can reach the target at the benchmark price in this configuration.", wrap=True)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=10)


# =============================================================================== profitability
def build_profitability(book):
    ws = book.ws(SH["prof"])
    title(ws, "Container Profitability – all configurations (selected scenario & destination)",
          "Revenue at benchmark price; contribution after selling costs and financing. Per-SKU contribution allocates selling costs by revenue.")
    widths = {c: 13 for c in "ABCDEFGHIJKLMNOPQRSTUV"}
    widths.update({"A": 5, "B": 46})
    set_widths(ws, widths)
    r = section(ws, 4, "1. Profitability by configuration", 22)
    hdr = ["#", "Configuration", "Fits?", "Units", "Containers", "Delivered COGS", "Revenue", "Gross profit", "GM", "Selling + financing", "Contribution", "CM",
           "Profit / container", "Peak WC", "Total cash", "Break-even price Δ", "Units needed GM 0", "Contrib 3464", "Contrib 3463", "Contrib 3460", "Cost/box", "Price/box"]
    r = header(ws, r, hdr)
    for i, c in enumerate(I.CONFIGS, 1):
        m = f"MATCH(sel_scen*1000+{i}*10+sel_dest,eng_key,0)"
        g = lambda k: f"INDEX(eng_{k},{m})"
        put(ws, r, 1, i)
        put(ws, r, 2, c["key"] + " " + c["name"])
        calc_cell(ws, r, 3, f"=IF({g('fits')},\"Yes\",\"NO\")")
        calc_cell(ws, r, 4, "=" + g("U"), FMT_INT)
        calc_cell(ws, r, 5, "=" + g("n"), "0")
        calc_cell(ws, r, 6, "=" + g("COGS"), FMT_USD0)
        calc_cell(ws, r, 7, "=" + g("REV"), FMT_USD0)
        calc_cell(ws, r, 8, "=" + g("GP"), FMT_USD0)
        calc_cell(ws, r, 9, "=" + g("GM"), FMT_PCT)
        calc_cell(ws, r, 10, f"={g('SELL_VAR')}+{g('SELL_FIX')}+{g('FIN')}", FMT_USD0)
        calc_cell(ws, r, 11, "=" + g("CONTRIB"), FMT_USD0, bold=True)
        calc_cell(ws, r, 12, "=" + g("CM"), FMT_PCT, bold=True)
        calc_cell(ws, r, 13, f"=IF({g('n')}>0,{g('CONTRIB')}/{g('n')},\"LCL\")", FMT_USD0)
        calc_cell(ws, r, 14, "=" + g("PEAK"), FMT_USD0)
        calc_cell(ws, r, 15, "=" + g("CASH_TOTAL"), FMT_USD0)
        calc_cell(ws, r, 16, f"={g('f_be')}-1", "+0.0%;-0.0%")
        calc_cell(ws, r, 17, "=" + g("u_be_0"), FMT_INT)
        for j, cc in enumerate(SKU_CODES):
            f = (f"={g('sale_' + cc)}*{g('price_' + cc)}-{g('cost_' + cc)}-IF({g('REV')}>0,({g('sale_' + cc)}*{g('price_' + cc)})/{g('REV')},0)*({g('SELL_VAR')}+{g('SELL_FIX')}+{g('FIN')})")
            calc_cell(ws, r, 18 + j, f, FMT_USD0)
        calc_cell(ws, r, 21, "=" + g("avg_cpb"), FMT_USD4)
        calc_cell(ws, r, 22, "=" + g("avg_price"), FMT_USD4)
        r += 1
    ws.conditional_formatting.add(f"K5:L{r - 1}", CellIsRule(operator="lessThan", formula=["0"], fill=FILL_BAD))
    ws.conditional_formatting.add(f"K5:L{r - 1}", CellIsRule(operator="greaterThanOrEqual", formula=["0"], fill=FILL_OK))
    r += 1
    r = section(ws, r, "2. Sell-through risk for the SELECTED configuration (if the whole lot is not sold at once)", 12)
    put(ws, r, 2, "Liquidation price for unsold stock (% of benchmark)")
    inp_cell(ws, r, 3, 0.5, FMT_PCT)
    liq = f"C{r}"
    r += 1
    put(ws, r, 2, "Storage cost per container-equivalent per month (USD)")
    inp_cell(ws, r, 3, 450, FMT_USD0)
    sto = f"C{r}"
    r += 1
    put(ws, r, 2, "Months unsold stock is stored before liquidation")
    inp_cell(ws, r, 3, 3, "0")
    mon = f"C{r}"
    r += 1
    r = header(ws, r, ["", "Share sold at benchmark price", "", "Revenue", "Contribution", "CM"])
    for share in (1.0, 0.9, 0.75, 0.5):
        put(ws, r, 2, "Sold at full price")
        inp_cell(ws, r, 3, share, FMT_PCT)
        rev = f"{S('REV')}*($C{r}+(1-$C{r})*{liq})"
        calc_cell(ws, r, 4, "=" + rev, FMT_USD0)
        contrib = (f"={rev}-{S('COGS')}-{rev}*{S('var_pct')}-{S('SELL_FIX')}-{S('FIN')}-(1-$C{r})*MAX({S('n')},1)*{sto}*{mon}")
        calc_cell(ws, r, 5, contrib, FMT_USD0)
        calc_cell(ws, r, 6, f"=IF(D{r}>0,E{r}/D{r},0)", FMT_PCT)
        r += 1
    put(ws, r, 2, "Storage and liquidation inputs are ASSUMED (no warehouse quote).", wrap=True)


# =============================================================================== sensitivity
def build_sensitivity(book, eng):
    ws = book.ws(SH["sens"])
    title(ws, "Sensitivity Analysis & Break-even (selected scenario, configuration and destination)",
          "Each line is a full engine recalculation with one driver changed (Calc Engine rows 'SENS'). Combination rows show what it would take to reach viability.")
    set_widths(ws, {"A": 5, "B": 56, "C": 14, "D": 14, "E": 12, "F": 12, "G": 14, "H": 14, "I": 10})
    r = section(ws, 4, "1. One-at-a-time sensitivity (tornado table)", 9)
    r = header(ws, r, ["#", "Driver change", "Cost / saleable box", "Δ cost / box", "GM", "CM", "Contribution", "Δ contribution", "Swing rank"])
    put(ws, r, 2, "BASE CASE (selected)", bold=True)
    calc_cell(ws, r, 3, "=" + S("avg_cpb"), FMT_USD4, bold=True)
    calc_cell(ws, r, 5, "=" + S("GM"), FMT_PCT, bold=True)
    calc_cell(ws, r, 6, "=" + S("CM"), FMT_PCT, bold=True)
    calc_cell(ws, r, 7, "=" + S("CONTRIB"), FMT_USD0, bold=True)
    base_r = r
    r += 1
    sens = E.sensitivity_cases(1)
    first = r
    for i, (label, ov) in enumerate(sens, 1):
        m = f"MATCH({900000 + i},eng_key,0)"
        put(ws, r, 1, i)
        put(ws, r, 2, label)
        calc_cell(ws, r, 3, f"=INDEX(eng_avg_cpb,{m})", FMT_USD4)
        calc_cell(ws, r, 4, f"=C{r}-$C${base_r}", "+0.0000;-0.0000")
        calc_cell(ws, r, 5, f"=INDEX(eng_GM,{m})", FMT_PCT)
        calc_cell(ws, r, 6, f"=INDEX(eng_CM,{m})", FMT_PCT)
        calc_cell(ws, r, 7, f"=INDEX(eng_CONTRIB,{m})", FMT_USD0)
        calc_cell(ws, r, 8, f"=G{r}-$G${base_r}", "+#,##0;-#,##0")
        r += 1
    last = r - 1
    # swing per pair (rows 1-30 are pairs)
    for k in range(0, 30, 2):
        r1, r2 = first + k, first + k + 1
        calc_cell(ws, r1, 9, f"=RANK(ABS(H{r1}-H{r2}),$J${first}:$J${first + 28})", "0")
        ws.cell(row=r1, column=10, value=f"=ABS(H{r1}-H{r2})").number_format = FMT_USD0
    ws.column_dimensions["J"].hidden = True
    ws.conditional_formatting.add(f"H{first}:H{last}", CellIsRule(operator="lessThan", formula=["0"], fill=FILL_BAD))
    ws.conditional_formatting.add(f"H{first}:H{last}", CellIsRule(operator="greaterThan", formula=["0"], fill=FILL_OK))
    r += 1
    r = section(ws, r, "2. Break-even conditions (selected case)", 9)
    r = header(ws, r, ["", "Condition", "Value", "Unit", "", "", "Interpretation"])
    bes = [
        ("Selling-price increase needed for contribution = 0", f"={S('f_be')}-1", FMT_PCT, "%", "vs achievable benchmark"),
        ("Supplier price change needed for GM = 0", "=" + S("chg_gm_0"), FMT_PCT, "% vs quote", "negative = discount required"),
        ("Supplier price change needed for GM = target", "=" + S("chg_gm_t"), FMT_PCT, "% vs quote", "target on Dashboard"),
        ("Maximum ocean freight per container for GM target", "=" + S("max_ocean"), FMT_USD0, "USD/ctr", "negative = unreachable even with free freight"),
        ("Units needed in same configuration for GM 0", "=" + S("u_be_0"), FMT_INT, "boxes", "compare with container capacity"),
        ("Units needed in same configuration for GM target", "=" + S("u_be_t"), FMT_INT, "boxes", "'n/a' = unreachable at this price"),
    ]
    for lab, f, fm, unit, interp in bes:
        put(ws, r, 2, lab)
        calc_cell(ws, r, 3, f, fm, bold=True)
        put(ws, r, 4, unit)
        put(ws, r, 7, interp)
        r += 1
    for j, c in enumerate(SKU_CODES):
        put(ws, r, 2, f"Max NFC price for GM target – SKU {c} (EGP, quote basis)")
        calc_cell(ws, r, 3, "=" + S(f"maxexw_{c}"), FMT_NUM3, bold=True)
        put(ws, r, 4, "EGP/box")
        put(ws, r, 7, f"quoted {[k['price_egp'] for k in I.SKUS if k['code'] == c][0]:.3f}")
        r += 1
    r += 1
    r = section(ws, r, "3. Path to viability – cumulative changes (BASE scenario, full 40' HC equal mix, selected destination)", 9)
    r = header(ws, r, ["#", "Combination", "Units", "Cost / box", "Price / box", "GM", "CM", "Contribution"])
    for i, (label, ci, ov) in enumerate(E.combo_cases(), 1):
        m = f"MATCH({950000 + i},eng_key,0)"
        put(ws, r, 1, i)
        put(ws, r, 2, label)
        calc_cell(ws, r, 3, f"=INDEX(eng_U,{m})", FMT_INT)
        calc_cell(ws, r, 4, f"=INDEX(eng_avg_cpb,{m})", FMT_USD4)
        calc_cell(ws, r, 5, f"=INDEX(eng_avg_price,{m})", FMT_USD4)
        calc_cell(ws, r, 6, f"=INDEX(eng_GM,{m})", FMT_PCT)
        calc_cell(ws, r, 7, f"=INDEX(eng_CM,{m})", FMT_PCT)
        calc_cell(ws, r, 8, f"=INDEX(eng_CONTRIB,{m})", FMT_USD0)
        r += 1
    ws.conditional_formatting.add(f"G{r - 6}:H{r - 1}", CellIsRule(operator="lessThan", formula=["0"], fill=FILL_BAD))
    ws.conditional_formatting.add(f"G{r - 6}:H{r - 1}", CellIsRule(operator="greaterThanOrEqual", formula=["0"], fill=FILL_OK))
    r += 1
    put(ws, r, 2, "Classification sensitivity: all candidate headings (4819.10, 4819.20, 4823.90.86, 4808.10) are MFN Free, so classification changes do not move duty unless an Annex II §301 exemption applies (equivalent to the '§301 duty 0%' row).", wrap=True)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=9)
    ws.row_dimensions[r].height = 32


# =============================================================================== scenario comparison
def build_scenarios(book):
    ws = book.ws(SH["scen"])
    title(ws, "Scenario Comparison – configurations × gateways/destinations, and option ranking",
          "Matrices use the scenario selected on the Dashboard. Ranking uses the selected destination.")
    widths = {c: 14 for c in "ABCDEFGHIJKLMNOP"}
    widths.update({"A": 5, "B": 46})
    set_widths(ws, widths)
    dests = [d["key"] + " " + d["port_name"].split(" ")[0] for d in I.DESTINATIONS]
    r = 4
    for lab, key, fm in [("A. Delivered cost per saleable box (USD)", "avg_cpb", FMT_USD4), ("B. Contribution margin", "CM", FMT_PCT), ("C. Contribution (USD)", "CONTRIB", FMT_USD0)]:
        r = section(ws, r, lab + " – selected scenario", 8)
        r = header(ws, r, ["#", "Configuration"] + dests)
        for i, c in enumerate(I.CONFIGS, 1):
            put(ws, r, 1, i)
            put(ws, r, 2, c["key"] + " " + c["name"])
            for j in range(len(I.DESTINATIONS)):
                calc_cell(ws, r, 3 + j, f"=INDEX(eng_{key},MATCH(sel_scen*1000+{i}*10+{j + 1},eng_key,0))", fm)
            r += 1
        if key != "avg_cpb":
            ws.conditional_formatting.add(f"C{r - 10}:G{r - 1}", CellIsRule(operator="lessThan", formula=["0"], fill=FILL_BAD))
            ws.conditional_formatting.add(f"C{r - 10}:G{r - 1}", CellIsRule(operator="greaterThanOrEqual", formula=["0"], fill=FILL_OK))
        r += 1
    r = section(ws, r, "D. Best gateway per configuration (lowest delivered cost, selected scenario)", 8)
    r = header(ws, r, ["#", "Configuration", "Best destination #", "Gateway → location", "Cost / box"])
    mat_first = 6
    for i, c in enumerate(I.CONFIGS, 1):
        rowA = mat_first + i - 1
        put(ws, r, 1, i)
        put(ws, r, 2, c["key"] + " " + c["name"])
        calc_cell(ws, r, 3, f"=MATCH(MIN(C{rowA}:G{rowA}),C{rowA}:G{rowA},0)", "0")
        calc_cell(ws, r, 4, f"=INDEX(dest_gw,C{r})&\" → \"&INDEX(dest_name,C{r})")
        calc_cell(ws, r, 5, f"=MIN(C{rowA}:G{rowA})", FMT_USD4)
        r += 1
    r += 1
    r = section(ws, r, "E. Multi-criteria ranking (selected scenario & destination) – weights and qualitative scores are editable", 16)
    weights = [("Risk-adjusted contribution", 0.30), ("Delivered cost/box", 0.15), ("Working capital", 0.10), ("Operational simplicity", 0.10),
               ("Price headroom", 0.15), ("Robustness (CM LOW−STRESS spread)", 0.10), ("Evidence quality", 0.10)]
    put(ws, r, 2, "Criterion →")
    for j, (lab, w) in enumerate(weights):
        put(ws, r, 3 + j, lab, wrap=True)
    ws.row_dimensions[r].height = 30
    r += 1
    put(ws, r, 2, "Weight →")
    for j, (lab, w) in enumerate(weights):
        inp_cell(ws, r, 3 + j, w, FMT_PCT)
    wrow = r
    r += 1
    r = header(ws, r, ["#", "Configuration", "Risk-adj. contribution (avg L/B/S × fits)", "Cost / box", "Peak WC", "Simplicity (1–5)", "Headroom %",
                       "CM spread", "Evidence (1–5)", "Score", "Rank", "Contribution (sel.)", "CM (sel.)", "Cost/box (sel.)", "Feasible all scenarios?"])
    first = r
    simplicity = {"C1": 4, "C2": 4, "C3": 3, "C4": 4, "C5": 5, "C6": 5, "C7": 5, "C8": 4, "C9": 4, "C10": 3}
    evidence = {"C1": 3, "C2": 2, "C3": 2, "C4": 2, "C5": 2, "C6": 2, "C7": 2, "C8": 2, "C9": 2, "C10": 1}
    for i, c in enumerate(I.CONFIGS, 1):
        mm = lambda s: f"MATCH({s}*1000+{i}*10+sel_dest,eng_key,0)"
        msel = f"MATCH(sel_scen*1000+{i}*10+sel_dest,eng_key,0)"
        put(ws, r, 1, i)
        put(ws, r, 2, c["key"] + " " + c["name"])
        calc_cell(ws, r, 3, "=(" + "+".join([f"INDEX(eng_CONTRIB,{mm(s)})" for s in (1, 2, 3)]) + ")/3*IF(AND(" + ",".join([f"INDEX(eng_fits,{mm(s)})" for s in (1, 2, 3)]) + "),1,0.5)", FMT_USD0)
        calc_cell(ws, r, 4, f"=INDEX(eng_avg_cpb,{msel})", FMT_USD4)
        calc_cell(ws, r, 5, f"=INDEX(eng_PEAK,{msel})", FMT_USD0)
        inp_cell(ws, r, 6, simplicity[c["key"]], "0")
        calc_cell(ws, r, 7, f"=IF(INDEX(eng_avg_price,{msel})>0,(INDEX(eng_avg_price,{msel})-INDEX(eng_avg_cpb,{msel}))/INDEX(eng_avg_price,{msel}),0)", FMT_PCT)
        calc_cell(ws, r, 8, f"=INDEX(eng_CM,{mm(1)})-INDEX(eng_CM,{mm(3)})", FMT_PCT)
        inp_cell(ws, r, 9, evidence[c["key"]], "0")
        r += 1
    last = r - 1
    for rr in range(first, last + 1):
        # min-max normalised scores (higher is better)
        def nz(colL, better_high=True):
            rng = f"${colL}${first}:${colL}${last}"
            core = f"({colL}{rr}-MIN({rng}))/MAX(MAX({rng})-MIN({rng}),0.000001)"
            return core if better_high else f"(1-{core})"
        score = (f"=$C${wrow}*{nz('C')}+$D${wrow}*{nz('D', False)}+$E${wrow}*{nz('E', False)}+$F${wrow}*{nz('F')}+$G${wrow}*{nz('G')}"
                 f"+$H${wrow}*{nz('H', False)}+$I${wrow}*{nz('I')}")
        calc_cell(ws, rr, 10, score, "0.000", bold=True)
        calc_cell(ws, rr, 11, f"=RANK(J{rr},$J${first}:$J${last})+COUNTIF($J${first}:J{rr},J{rr})-1", "0")
        i = rr - first + 1
        msel = f"MATCH(sel_scen*1000+{i}*10+sel_dest,eng_key,0)"
        calc_cell(ws, rr, 12, f"=INDEX(eng_CONTRIB,{msel})", FMT_USD0)
        calc_cell(ws, rr, 13, f"=INDEX(eng_CM,{msel})", FMT_PCT)
        calc_cell(ws, rr, 14, f"=INDEX(eng_avg_cpb,{msel})", FMT_USD4)
        calc_cell(ws, rr, 15, "=IF(AND(" + ",".join([f"INDEX(eng_fits,MATCH({s}*1000+{i}*10+sel_dest,eng_key,0))" for s in (1, 2, 3)]) + "),\"Yes\",\"No\")")
    book.name("scomp_rank", ws.title, f"K{first}:K{last}")
    book.name("scomp_cfgname", ws.title, f"B{first}:B{last}")
    book.name("scomp_contrib", ws.title, f"L{first}:L{last}")
    book.name("scomp_cm", ws.title, f"M{first}:M{last}")
    book.name("scomp_cpb", ws.title, f"N{first}:N{last}")
    r += 1
    put(ws, r, 2, "Ranking ranks options relative to each other; a top rank does NOT mean the option is viable – check contribution sign and Dashboard thresholds.", wrap=True, font=F_WARN)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=12)


# =============================================================================== cash flow
def build_cash(book):
    ws = book.ws(SH["cash"])
    title(ws, "Cash Flow & Working Capital – selected case", "Days from purchase order (day 0). Recoverable VAT shown as a deposit-like outflow and later inflow.")
    set_widths(ws, {"A": 5, "B": 46, "C": 10, "D": 16, "E": 16, "F": 18, "G": 50})
    r = section(ws, 4, "1. Timeline", 7)
    r = header(ws, r, ["#", "Event", "Day", "Outflow USD", "Inflow USD", "Cumulative net USD", "Content"])
    ev = [
        ("Purchase order: advance to supplier, tooling, samples/testing", "0", S("out0"), "0", "advance % × (supplier + VAT) + tooling + testing"),
        ("Collection / export: balance, origin costs, prepaid ocean freight, insurance", S("t1"), S("out1"), "0", "(1 − advance) × (supplier + VAT) + origin + ocean + insurance"),
        ("Egyptian VAT refund (mode 2 only)", S("tref"), "0", S("vatref"), "45-day statutory refund after documented application"),
        ("US arrival & entry: duty, MPF, HMF, broker, bonds, port charges", S("t2"), S("out2"), "0", ""),
        ("Delivery to customer: drayage, accessorials, unloading", S("t3"), S("out3"), "0", ""),
        ("Customer payment (revenue at benchmark price)", S("t4"), "0", S("REV"), "net of nothing – commission & bad debt below"),
    ]
    first = r
    for i, (lab, d, o, inn, note) in enumerate(ev, 1):
        put(ws, r, 1, i)
        put(ws, r, 2, lab, wrap=True)
        calc_cell(ws, r, 3, "=" + d, "0")
        calc_cell(ws, r, 4, "=" + o, FMT_USD0)
        calc_cell(ws, r, 5, "=" + inn, FMT_USD0)
        put(ws, r, 7, note, wrap=True)
        ws.row_dimensions[r].height = 30
        r += 1
    last = r - 1
    for rr in range(first, last + 1):
        calc_cell(ws, rr, 6, f"=SUMPRODUCT(($C${first}:$C${last}<=C{rr})*($D${first}:$D${last}-$E${first}:$E${last}))", FMT_USD0)
    r += 1
    r = section(ws, r, "2. Cash requirements (brief §13.2)", 7)
    for lab, f in [("Cash required before shipment", S("out0")), ("Cash required at export", S("out1")), ("Cash required before US release", S("out2")),
                   ("Cash required at delivery", S("out3")), ("Total transaction cash outflow", S("CASH_TOTAL")), ("VAT refund receivable (mode 2)", S("vatref")),
                   ("PEAK working capital (before customer receipt)", S("PEAK")), ("Financing cost (annual rate × $-days / 365)", S("FIN")),
                   ("One-time importer set-up (not in per-box cost)", "INDEX(in_sel_setup,1,sel_scen)")]:
        put(ws, r, 2, lab, bold=lab.startswith("PEAK") or lab.startswith("Total"))
        calc_cell(ws, r, 4, "=" + f, FMT_USD0, bold=lab.startswith("PEAK"))
        r += 1
    r += 1
    r = section(ws, r, "3. VAT treatment comparison (selected configuration; sensitivity rows)", 7)
    r = header(ws, r, ["", "VAT view", "", "VAT cash", "Economic VAT", "Peak WC", "Contribution"])
    rows = [("Scenario default (BASE = mode 2: paid & refunded)", "sel_row"),
            ("Mode 1: zero-rated direct export", f"MATCH({900000 + 17},eng_key,0)"),
            ("Mode 3: paid, not recoverable", f"MATCH({900000 + 18},eng_key,0)")]
    for lab, m in rows:
        put(ws, r, 2, lab)
        for j, k in enumerate(["VAT_CASH", "VAT_ECON", "PEAK", "CONTRIB"]):
            calc_cell(ws, r, 4 + j, f"=INDEX(eng_{k},{m})", FMT_USD0)
        r += 1
    r += 1
    put(ws, r, 2, "Avoid double-counting: VAT appears either as a refundable cash item (mode 2) or as an economic cost (mode 3), never both. Sales tax in the US is not an import duty and is not modelled for B2B resale.", wrap=True)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=7)
    ws.row_dimensions[r].height = 30


# =============================================================================== registers
def build_risk(book):
    ws = book.ws(SH["risk"])
    title(ws, "Risk Register", "Likelihood and impact 1–5; score = L × I. Ordered by ID; see score for priority.")
    set_widths(ws, {"A": 6, "B": 58, "C": 14, "D": 10, "E": 9, "F": 8, "G": 70, "H": 20, "I": 22})
    r = header(ws, 4, ["ID", "Risk", "Category", "Likelihood", "Impact", "Score", "Mitigation", "Owner", "Status"])
    for rid, risk, cat, l, i, mit, own, st in R.RISKS:
        put(ws, r, 1, rid)
        put(ws, r, 2, risk, wrap=True)
        put(ws, r, 3, cat)
        inp_cell(ws, r, 4, l, "0")
        inp_cell(ws, r, 5, i, "0")
        calc_cell(ws, r, 6, f"=D{r}*E{r}", "0", bold=True)
        put(ws, r, 7, mit, wrap=True)
        put(ws, r, 8, own)
        put(ws, r, 9, st, wrap=True)
        ws.row_dimensions[r].height = 30
        r += 1
    ws.conditional_formatting.add(f"F5:F{r - 1}", CellIsRule(operator="greaterThanOrEqual", formula=["15"], fill=FILL_BAD))
    ws.conditional_formatting.add(f"F5:F{r - 1}", CellIsRule(operator="between", formula=["8", "14"], fill=FILL_AMBER))
    ws.conditional_formatting.add(f"F5:F{r - 1}", CellIsRule(operator="lessThan", formula=["8"], fill=FILL_OK))
    list_validation(ws, f"D5:E{r - 1}", [1, 2, 3, 4, 5])


IMPACT = {  # decision impact of inputs (judgement informed by sensitivity swings)
    "listing_3464": "High", "listing_3463": "High", "listing_3460": "High", "dist_margin": "High", "eflute_disc": "High",
    "s301": "High", "requote": "High", "cbe": "Medium", "rate_20": "High", "rate_40": "High", "rate_hc": "High", "vat_mode": "Medium",
    "pitch": "Medium", "efficiency": "Medium", "k_len": "Medium", "per_bundle": "Low", "grammage": "Low", "damage": "Medium",
    "testing": "Medium", "commission": "Medium", "unload_40": "Medium", "truck_40": "Low", "fsc": "Low", "credit_days": "Low",
}


def build_assumptions(book):
    ws = book.ws(SH["assum"])
    title(ws, "Assumptions Register – every model input, its evidence and decision impact",
          "Values are live links to the input cells. ⚠ = ASSUMED/ESTIMATED/UNRESOLVED input with High decision impact (shown as a Dashboard warning).")
    set_widths(ws, {"A": 12, "B": 18, "C": 56, "D": 12, "E": 12, "F": 12, "G": 12, "H": 20, "I": 18, "J": 10, "K": 30, "L": 60})
    r = header(ws, 4, ["Group", "Key", "Input", "Unit", "LOW", "BASE", "STRESS", "Evidence", "Sources", "Impact", "Flag", "Notes / method"])
    prefix_of = {"Engineering": "eng", "Container": "use", "FX": "fx", "Supplier": "sup", "Origin": "ori", "Ocean": "oce", "US customs": "cus",
                 "Destination": "dra", "Selling": "sel", "Market": "mkt"}
    first = r
    for grp, key, d in I.all_inputs():
        nm = f"in_{prefix_of[grp]}_{key}"
        put(ws, r, 1, grp)
        put(ws, r, 2, key)
        put(ws, r, 3, d["name"], wrap=True)
        put(ws, r, 4, d["unit"])
        fm = fmt_for_unit(d["unit"])
        for j in range(3):
            calc_cell(ws, r, 5 + j, f"=INDEX({nm},1,{j + 1})", fm)
        put(ws, r, 8, d["evidence"])
        put(ws, r, 9, d["sources"], wrap=True)
        imp = IMPACT.get(key, "Low")
        put(ws, r, 10, imp)
        calc_cell(ws, r, 11, f'=IF(AND(J{r}="High",OR(H{r}="ASSUMED",H{r}="ESTIMATED",H{r}="UNRESOLVED")),"⚠ decision-relevant, unverified","")')
        put(ws, r, 12, d.get("note", ""), wrap=True)
        r += 1
    # destinations and port differentials (table inputs)
    for d in I.DESTINATIONS:
        for lab, vals in [("linehaul", d["line"]), ("tolls", d["tolls"]), ("chassis $/day", d["chassis"])]:
            put(ws, r, 1, "Destination")
            put(ws, r, 2, f"{d['key']}_{lab}")
            put(ws, r, 3, f"{d['port_name']} → {d['city']}: {lab}", wrap=True)
            put(ws, r, 4, "USD")
            for j in range(3):
                static_cell(ws, r, 5 + j, vals[j], FMT_USD0)
            put(ws, r, 8, "ESTIMATED")
            put(ws, r, 9, "S052;S053;S054;S094")
            put(ws, r, 10, "High" if lab == "linehaul" else "Low")
            calc_cell(ws, r, 11, f'=IF(AND(J{r}="High",OR(H{r}="ASSUMED",H{r}="ESTIMATED",H{r}="UNRESOLVED")),"⚠ decision-relevant, unverified","")')
            put(ws, r, 12, "Source of truth: 'Destination Delivery' table (this row is a copy for the register)")
            r += 1
    last = r - 1
    evidence_cf(ws, f"H{first}:H{last}")
    book.name("asm_flag", ws.title, f"K{first}:K{last}")


def build_sources(book):
    ws = book.ws(SH["src"])
    title(ws, "Source Register", "Full register also exported as BigBoxPizza_Source_Register.csv (UTF-8). Access method recorded for every source.")
    set_widths(ws, {"A": 7, "B": 50, "C": 26, "D": 45, "E": 14, "F": 11, "G": 30, "H": 60, "I": 50, "J": 18, "K": 22, "L": 16, "M": 40})
    r = header(ws, 4, ["ID", "Title", "Organisation", "URL / path", "Pub. / rev. date", "Access date", "Access method", "Relevant extract", "Claim supported",
                       "Primary / secondary", "Evidence class", "Confidence", "Limitation"])
    for s in sorted(SD.SOURCES, key=lambda x: x["id"]):
        vals = [s["id"], s["title"], s["org"], s["url"], s["pub_date"], s["access_date"], s["method"], s["extract"], s["claim"], s["ptype"], s["evidence"],
                s["confidence"], s["limitation"]]
        for j, v in enumerate(vals):
            put(ws, r, 1 + j, v, wrap=True)
        ws.row_dimensions[r].height = 60
        r += 1
    evidence_cf(ws, f"K5:K{r - 1}")


def build_rfq(book):
    ws = book.ws(SH["rfq"])
    title(ws, "Quote Requests & Missing Data", "Ranked by impact and urgency. 'Blocks' = SHIPMENT (resolve before paying/shipping), PRICING (decision-relevant) or PRECISION.")
    set_widths(ws, {"A": 6, "B": 50, "C": 40, "D": 34, "E": 34, "F": 40, "G": 26, "H": 11, "I": 8, "J": 12})
    r = header(ws, 4, ["ID", "Missing fact", "Why it matters", "Potential impact", "Provisional treatment", "Evidence required", "Best placed to supply", "Blocks", "Priority", "Status"])
    first = r
    for g in sorted(R.GAPS, key=lambda x: x["priority"]):
        vals = [g["id"], g["fact"], g["why"], g["impact"], g["treatment"], g["evidence"], g["who"], g["blocks"], g["priority"]]
        for j, v in enumerate(vals):
            put(ws, r, 1 + j, v, wrap=True)
        inp_cell(ws, r, 10, "Open")
        ws.row_dimensions[r].height = 64
        r += 1
    last = r - 1
    list_validation(ws, f"J{first}:J{last}", ["Open", "Requested", "Received", "Resolved"])
    book.name("rfq_blocks", ws.title, f"H{first}:H{last}")
    book.name("rfq_status", ws.title, f"J{first}:J{last}")
    r += 1
    r = section(ws, r, "RFQ tracker (full texts in BigBoxPizza_RFQ_Pack.md)", 10)
    r = header(ws, r, ["RFQ", "Recipient", "Purpose", "Status", "Targets"])
    for rq in R.RFQS:
        for j, v in enumerate(rq):
            put(ws, r, 1 + j, v, wrap=True)
        r += 1


def build_checks(book, eng):
    ws = book.ws(SH["chk"])
    title(ws, "Model Checks – formula integrity, reconciliation and double-count controls", "All checks should read OK. Overall status feeds the Dashboard.")
    set_widths(ws, {"A": 6, "B": 70, "C": 40, "D": 60})
    r = header(ws, 4, ["#", "Check", "Status", "What it tests"])
    rr0 = r
    e0, el = eng["r0"], eng["rl"]
    cm = eng["colmap"]
    checks = [
        ("Quote line totals = qty × unit price", '=IF(SUMPRODUCT(ABS(q_diff))<0.01,"OK","FAIL")', "Line arithmetic"),
        ("Quote subtotal reconciles", "=q_chk_subtotal", "463,300"),
        ("Quote tax = 14% × subtotal", "=q_chk_tax", "64,862"),
        ("Quote total reconciles", "=q_chk_total", "528,162"),
        ("Quoted quantity = 60,000", "=q_chk_qty", "20,000 × 3"),
        ("Fixed configurations C1–C3 total 60,000 units in every scenario", '=IF(AND(INDEX(cfg_total,1,1)=60000,INDEX(cfg_total,1,2)=60000,INDEX(cfg_total,1,3)=60000,INDEX(cfg_total,2,2)=60000,INDEX(cfg_total,3,2)=60000),"OK","FAIL")', "Inconsistent quantities"),
        ("Engine: SKU cost allocation sums to COGS on every row", '=IF(SUMPRODUCT((ABS(eng_alloc_chk)>0.01)*1)=0,"OK","FAIL")', "Allocation integrity (all engine rows)"),
        ("Ledger economic total = engine COGS (selected case)", "=led_chk_cogs", "Ledger vs engine"),
        ("No duplicate cost IDs in ledger", "=led_chk_dup", "Duplicate cost lines"),
        ("Origin ledger lines = engine ORIGIN", "=led_chk_origin", "Origin bundling"),
        ("Ocean + insurance ledger = engine", "=led_chk_ocean", "Freight/insurance"),
        ("US duty/fees ledger = engine", "=led_chk_duty", "Customs fees"),
        ("Delivery & disruption ledger = engine", "=led_chk_delivery", "Drayage/unloading"),
        ("SKU allocation table total = engine COGS", "=led_chk_alloc", "Per-SKU reconciliation"),
        ("Supplier quotation reconciles to shipment value (when units = quoted mix)", "=led_chk_recon", "Quote → shipment value"),
        ("Customs value build-up = engine customs value", "=tar_cv_check", "Customs value"),
        ("Double-count flag: origin THC not also in ocean freight", '=IF(INDEX(in_ori_othc_in_freight,1,sel_scen)=0,"OK – THC charged once (ocean estimate excludes OTHC)","OK – THC excluded (in freight)")', "Terminal handling in freight"),
        ("Double-count flag: CFC / insurance / chassis / unloading", '=IF(AND(INDEX(in_cus_cfc_in_freight,1,sel_scen)<=1,INDEX(in_oce_ins_in_other,1,sel_scen)<=1,INDEX(in_dra_chassis_in_dray,1,sel_scen)<=1,INDEX(in_dra_unload_in_dray,1,sel_scen)<=1),"OK – flags set (each item once)","FAIL")', "Bundled charges"),
        ("Recoverable VAT excluded from COGS unless mode 3", f'=IF(SUMPRODUCT((eng_vatmode<>3)*(ABS(eng_VAT_ECON)>0.0001))=0,"OK","FAIL")', "Tax treated once"),
        ("Equal-mix maxima (script values) still fit in all scenarios", '=IF(AND(INDEX(cfg_fits,4,1),INDEX(cfg_fits,4,2),INDEX(cfg_fits,4,3),INDEX(cfg_fits,8,1),INDEX(cfg_fits,8,2),INDEX(cfg_fits,8,3),INDEX(cfg_fits,9,1),INDEX(cfg_fits,9,2),INDEX(cfg_fits,9,3)),"OK","WARN – re-run scripts/build_all.py (geometry inputs changed)")', "Static values vs formulas"),
        ("Floor pattern equals exact DP optimum (all SKU × container × scenario)", '=IF(COUNTIF(lg_validation,"OK*")=ROWS(lg_validation),"OK","WARN – see Loading Geometry col AH")', "Packing algorithm validation"),
        ("No error values in engine key outputs", f'=IF(SUMPRODUCT(ISERROR(eng_COGS)*1)+SUMPRODUCT(ISERROR(eng_REV)*1)+SUMPRODUCT(ISERROR(eng_CONTRIB)*1)+SUMPRODUCT(ISERROR(eng_PEAK)*1)=0,"OK","ERROR")', "Missing data handled"),
        ("Supplier quotation expired (information)", '=IF(val_date>q_valid_until,"WARN – expired quote used as historical reference","OK")', "Validity"),
        ("FX observation within 7 days of valuation date", '=IF(ABS(val_date-DATE(2026,10,15))<=7,"OK","WARN – refresh FX")', "Exchange-rate date"),
    ]
    for i, (lab, f, what) in enumerate(checks, 1):
        put(ws, r, 1, i)
        put(ws, r, 2, lab, wrap=True)
        calc_cell(ws, r, 3, f)
        put(ws, r, 4, what, wrap=True)
        r += 1
    last = r - 1
    status_cf(ws, f"C{rr0}:C{last}")
    r += 1
    put(ws, r, 2, "OVERALL STATUS", bold=True)
    calc_cell(ws, r, 3, f'=IF(COUNTIF(C{rr0}:C{last},"FAIL*")+COUNTIF(C{rr0}:C{last},"ERROR*")>0,"FAIL – see Model Checks",IF(COUNTIF(C{rr0}:C{last},"WARN*")>0,"WARN – "&COUNTIF(C{rr0}:C{last},"WARN*")&" warning(s), no failures","OK – all checks pass"))', bold=True)
    book.name("chk_overall", ws.title, f"C{r}")
    status_cf(ws, f"C{r}:C{r}")
