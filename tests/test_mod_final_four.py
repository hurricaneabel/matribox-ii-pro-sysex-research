"""Regressões finais dos quatro MOD restantes e encerramento da classe MOD (Fase 78)."""
from __future__ import annotations
import json, struct, tempfile, unittest
from pathlib import Path
from tools.catalog import load_effect_catalog
from tools.commands.chain_order import ChainOrderState
from tools.commands.effect_catalog import CATALOG, EFFECT_CLASSES
from tools.commands.preset_monitor_core import build_effect_snapshots
from tools.commands.structural_effect_state import StructuralEffectRecord
from tools.migrations.export_effect_catalog_to_json import export_catalog
from tools.parameters import parse_effect_parameter_response
from tools.parameters.state import EffectParameterState

EXPECTED = {
    "mod.d_chorus": (("mode",0),),
    "mod.m_chorus": (("mix",0),("rate",1),("filter",2),("depth_l",3),("depth_c",4),("depth_r",5),("sync",6)),
    "mod.detune": (("detune",0),("wet",1),("dry",2)),
    "mod.lofi_bit": (("mix",0),("krush",1),("bit",2),("hi_cut",3),("lo_cut",4)),
}

def make_chain(effect_key: str) -> ChainOrderState:
    effect=CATALOG.effect_by_key(effect_key); cls=CATALOG.class_by_key(effect.class_key)
    records=[]; enabled=[None]*12
    for slot in range(12):
        if slot==0:
            enabled[slot]=True; records.append(StructuralEffectRecord(slot,True,cls.class_id,effect.model_id,0,0,effect.secondary_selector,True))
        else: records.append(StructuralEffectRecord(slot,False,None,None,0,0,None,None))
    return ChainOrderState((0,),0,0,b"",tuple(enabled),tuple(records))

def make_msg(selector:int,value:float)->bytes:
    b=bytearray((Path("tests/fixtures/eq_parameters")/"guitar_eq1_volume_083.bin").read_bytes()); b[48]=selector
    raw=struct.pack("<f",float(value)); n=[]
    for x in raw:n.extend((x>>4,x&15))
    b[55:63]=bytes(n); return bytes(b)

class ModFinalFourPhase78Tests(unittest.TestCase):
    def test_final_schemas_defaults_and_global_counts(self):
        catalog=load_effect_catalog()
        for key, expected in EXPECTED.items():
            e=catalog.effect_by_key(key)
            self.assertEqual(e.parameter_catalog_status, "physically_validated")
            self.assertEqual(tuple((p.key,p.message_match["parameter_selector"]) for p in e.parameters),expected)
            for p in e.parameters:
                self.assertTrue(p.validation["physical"])
                self.assertFalse(p.validation["candidate_requires_live_validation"])
                self.assertEqual(p.value_codec,"float32_nibbles_v1")
        d=catalog.effect_by_key("mod.d_chorus")
        self.assertEqual(tuple(d.parameters[0].choices.keys()),(0,1,2,3))
        self.assertEqual(tuple(d.parameters[0].choices.values()),("1","2","3","4"))
        self.assertEqual(d.parameters[0].validation["saved_dump_default"],0)
        self.assertEqual(d.parameters[0].validation["ui_default_label"],"1")
        m=catalog.effect_by_key("mod.m_chorus"); self.assertEqual([p.validation.get("saved_dump_default") for p in m.parameters if p.key!="rate"],[50,50,50,50,50,0])
        det=catalog.effect_by_key("mod.detune"); self.assertEqual(det.parameters[0].minimum,-50); self.assertEqual(det.parameters[0].maximum,50); self.assertEqual(det.parameters[0].validation["saved_dump_default"],-25)
        lo=catalog.effect_by_key("mod.lofi_bit"); self.assertEqual([p.validation["saved_dump_default"] for p in lo.parameters],[50,20,20,50,50])
        statuses={}; total=0
        for c in catalog.classes:
            for e in c.models: statuses[e.parameter_catalog_status]=statuses.get(e.parameter_catalog_status,0)+1; total+=len(e.parameters)
        self.assertEqual(catalog.catalog_version,59); self.assertEqual(statuses,{"physically_validated":224,"pending":43}); self.assertEqual(total,922)

    def test_monitor_renders_final_values_and_m_chorus_sync(self):
        cases=(
            ("mod.d_chorus",((0,0),(0,1),(0,3)),{"mode":"4"}),
            ("mod.detune",((0,-37),(1,73),(2,29)),{"detune":"-37 cents","wet":"73","dry":"29"}),
            ("mod.lofi_bit",((0,66),(1,31),(2,24),(3,81),(4,17)),{"mix":"66","krush":"31","bit":"24","hi_cut":"81","lo_cut":"17"}),
        )
        for key,events,expected in cases:
            state=EffectParameterState(CATALOG); chain=make_chain(key)
            for sel,val in events:
                ev=parse_effect_parameter_response(make_msg(sel,val),effect_key=key); self.assertIsNotNone(ev); state.apply(ev)
            by={p.key:p.display_value for p in build_effect_snapshots(chain,state)[0].parameters}
            for k,v in expected.items(): self.assertEqual(by[k],v)
        key="mod.m_chorus"; state=EffectParameterState(CATALOG); chain=make_chain(key)
        for sel,val in ((0,61),(1,3.7),(2,42),(3,53),(4,64),(5,75)):
            ev=parse_effect_parameter_response(make_msg(sel,val),effect_key=key); self.assertIsNotNone(ev); state.apply(ev)
        by={p.key:p.display_value for p in build_effect_snapshots(chain,state)[0].parameters}; self.assertEqual(by["rate"],"3.7 Hz")
        ev=parse_effect_parameter_response(make_msg(6,1),effect_key=key); state.apply(ev)
        by={p.key:p.display_value for p in build_effect_snapshots(chain,state)[0].parameters}; self.assertEqual(by["sync"],"ligado"); self.assertEqual(by["rate"],"1/4")
        ev=parse_effect_parameter_response(make_msg(1,8),effect_key=key); state.apply(ev); by={p.key:p.display_value for p in build_effect_snapshots(chain,state)[0].parameters}; self.assertEqual(by["rate"],"1/8d")
        ev=parse_effect_parameter_response(make_msg(6,0),effect_key=key); state.apply(ev); by={p.key:p.display_value for p in build_effect_snapshots(chain,state)[0].parameters}; self.assertEqual(by["rate"],"0.5 Hz")

    def test_exporter_reproduces_four_final_jsons(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"catalog"; export_catalog(EFFECT_CLASSES,root)
            self.assertEqual(json.loads((root/"catalog.json").read_text())["catalog_version"],59)
            for key in EXPECTED:
                e=CATALOG.effect_by_key(key); name=f"{e.menu_number:03d}_{key.split('.',1)[1]}.json"
                ex=json.loads((root/"effects/mod"/name).read_text()); cur=json.loads((Path("catalog/effects/mod")/name).read_text())
                self.assertEqual(ex["parameters"],cur["parameters"])
                self.assertEqual(ex["parameter_catalog_status"], "physically_validated")
                self.assertTrue(all(p["validation"]["physical"] for p in ex["parameters"]))

if __name__ == "__main__": unittest.main()
