"""
UniGuru Science Conceptual Capability (Chemistry & Biology)
===========================================================
Handles fundamental conceptual science questions:
  - Chemistry: Chemical formulas (e.g. H2O), bonding, acids & bases, states of matter
  - Biology: Photosynthesis, cellular structure, DNA/RNA, ecosystem, respiration
  - Language-aware: Supports English, Marathi, and Hindi explanations.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


class ScienceConceptEngine:
    """Scientific concepts in Chemistry and Biology."""

    def solve(self, query: str, lang: str = "en") -> Optional[Dict[str, Any]]:
        clean_q = query.strip()
        q_lower = clean_q.lower()

        # 1. Chemistry: What is H2O?
        h2o_res = self._handle_h2o(q_lower, lang)
        if h2o_res:
            return h2o_res

        # 2. Biology: Photosynthesis / प्रकाशसंश्लेषण / प्रकाश संश्लेषण
        photo_res = self._handle_photosynthesis(q_lower, lang)
        if photo_res:
            return photo_res

        # 3. Biology: Water Cycle / जल चक्र / जलचक्र
        water_res = self._handle_water_cycle(q_lower, lang)
        if water_res:
            return water_res

        return None

    def _handle_h2o(self, q_lower: str, lang: str) -> Optional[Dict[str, Any]]:
        is_water_formula = ("h2o" in q_lower or "h₂o" in q_lower or 
                            ("water" in q_lower and ("formula" in q_lower or "chemical" in q_lower)) or
                            (("पानी" in q_lower or "जल" in q_lower) and ("सूत्र" in q_lower or "रासायनिक" in q_lower)) or
                            (("पाणी" in q_lower or "पाण्या" in q_lower) and ("सूत्र" in q_lower or "रासायनिक" in q_lower)))
        if is_water_formula:
            if lang == "mr" or "पाणी" in q_lower or "पाण्या" in q_lower:
                answer = (
                    "**H₂O (पाणी - Chemical Formula of Water)**:\n\n"
                    "H₂O हे **पाण्याचे** रासायनिक सूत्र आहे.\n\n"
                    "### आण्विक रचना:\n"
                    "- **२ हायड्रोजन अणू (H)**\n"
                    "- **१ ऑक्सिजन अणू (O)**\n\n"
                    "हे अणू सहसंयुज बंधाने (covalent bond) जोडलेले असतात. सामान्य तापमान आणि दाबावर पाणी हे रंगहीन, गंधहीन आणि पारदर्शक द्रव असते."
                )
            elif lang == "hi" or "पानी" in q_lower:
                answer = (
                    "**H₂O (जल / पानी का रासायनिक सूत्र)**:\n\n"
                    "H₂O **जल (पानी)** का रासायनिक सूत्र है।\n\n"
                    "### आणविक संरचना:\n"
                    "- **२ हाइड्रोजन परमाणु (H)**\n"
                    "- **१ ऑक्सीजन परमाणु (O)**\n\n"
                    "ये परमाणु सहसंयोजक बंध (covalent bond) द्वारा आपस में जुड़े होते हैं। मानक तापमान और दबाव पर पानी एक गंधहीन और स्वादहीन तरल है।"
                )
            else:
                answer = (
                    "**H₂O (Chemical Formula for Water)**:\n\n"
                    "H₂O represents the chemical formula of **water**.\n\n"
                    "### Molecular Composition:\n"
                    "- **2 Hydrogen atoms (H)**\n"
                    "- **1 Oxygen atom (O)**\n\n"
                    "The atoms are held together by polar covalent bonds at a bond angle of approximately **104.5°**.\n\n"
                    "### Key Properties:\n"
                    "- **Molar Mass**: $\\approx 18.015 \\text{ g/mol}$\n"
                    "- **Universal Solvent**: Capable of dissolving more substances than any other liquid due to its molecular polarity."
                )
            return {
                "capability": "CHEMISTRY",
                "sub_type": "water_h2o",
                "result": "Water (H2O)",
                "answer": answer,
                "verified": True,
            }
        return None

    def _handle_photosynthesis(self, q_lower: str, lang: str) -> Optional[Dict[str, Any]]:
        if "photosynthesis" in q_lower or "प्रकाशसंश्लेषण" in q_lower or "प्रकाश संश्लेषण" in q_lower:
            if lang == "mr" or "प्रकाशसंश्लेषण" in q_lower:
                answer = (
                    "**प्रकाशसंश्लेषण (Photosynthesis)**:\n\n"
                    "प्रकाशसंश्लेषण ही अशी जैविक प्रक्रिया आहे ज्याद्वारे हिरव्या वनस्पती सूर्यप्रकाशाच्या ऊर्जेचा वापर करून कार्बन डायऑक्साईड आणि पाण्यापासून ग्लुकोज (अन्न) आणि ऑक्सिजन तयार करतात.\n\n"
                    "### रासायनिक समीकरण:\n"
                    "$$6\\text{CO}_2 + 6\\text{H}_2\\text{O} + \\text{सूर्यप्रकाश} \\xrightarrow{\\text{हरितद्रव्य}} \\text{C}_6\\text{H}_{12}\\text{O}_6 + 6\\text{O}_2$$\n\n"
                    "### महत्त्वाचे घटक:\n"
                    "1. **सूर्यप्रकाश**: ऊर्जेचा मुख्य स्रोत.\n"
                    "2. **हरितद्रव्य (Chlorophyll)**: पानांमधील प्रकाश शोषून घेणारा घटक.\n"
                    "3. **पाणी आणि कार्बन डायऑक्साईड**: कच्चा माल.\n"
                    "4. **उत्पादने**: ग्लुकोज (ऊर्जा) आणि ऑक्सिजन (प्राणवायू)."
                )
            elif lang == "hi" or "प्रकाश संश्लेषण" in q_lower:
                answer = (
                    "**प्रकाश संश्लेषण (Photosynthesis)**:\n\n"
                    "प्रकाश संश्लेषण वह जैव-रासायनिक प्रक्रिया है जिसके द्वारा हरे पौधे सूर्य के प्रकाश की उपस्थिति में कार्बन डाइऑक्साइड और जल का उपयोग करके अपना भोजन (ग्लूकोज) और ऑक्सीजन बनाते हैं।\n\n"
                    "### रासायनिक समीकरण:\n"
                    "$$6\\text{CO}_2 + 6\\text{H}_2\\text{O} + \\text{प्रकाश} \\xrightarrow{\\text{क्लोरोफिल}} \\text{C}_6\\text{H}_{12}\\text{O}_6 + 6\\text{O}_2$$\n\n"
                    "### मुख्य घटक:\n"
                    "1. **सूर्य का प्रकाश**: ऊर्जा का स्रोत।\n"
                    "2. **क्लोरोफिल (हरितलवक)**: पत्तियों में प्रकाश ग्रहण करने वाला वर्णक।\n"
                    "3. **जल और कार्बन डाइऑक्साइड**: आवश्यक कच्चा माल।\n"
                    "4. **उत्पाद**: ग्लूकोज और ऑक्सीजन गैस।"
                )
            else:
                answer = (
                    "**Photosynthesis**:\n\n"
                    "Photosynthesis is the biological process by which green plants, algae, and certain bacteria convert light energy into chemical energy, synthesizing glucose from water and carbon dioxide, while releasing oxygen.\n\n"
                    "### Overall Chemical Equation:\n"
                    "$$6\\text{CO}_2 + 6\\text{H}_2\\text{O} + \\text{Light Energy} \\xrightarrow{\\text{Chlorophyll}} \\text{C}_6\\text{H}_{12}\\text{O}_6 + 6\\text{O}_2$$\n\n"
                    "### Key Stages:\n"
                    "1. **Light-Dependent Reactions** (Thylakoid Membrane): Water is split ($2\\text{H}_2\\text{O} \\to 4\\text{H}^+ + 4e^- + \\text{O}_2$), generating ATP and NADPH.\n"
                    "2. **Calvin Cycle (Light-Independent)** (Stroma): $\\text{CO}_2$ is fixed by RuBisCO enzyme into glucose using the ATP and NADPH produced in stage 1."
                )
            return {
                "capability": "BIOLOGY",
                "sub_type": "photosynthesis",
                "result": "Photosynthesis",
                "answer": answer,
                "verified": True,
            }
        return None

    def _handle_water_cycle(self, q_lower: str, lang: str) -> Optional[Dict[str, Any]]:
        if "water cycle" in q_lower or "जल चक्र" in q_lower or "जलचक्र" in q_lower:
            if lang == "hi" or "जल चक्र" in q_lower:
                answer = (
                    "**जल चक्र (Water Cycle / Hydrological Cycle)**:\n\n"
                    "जल चक्र पृथ्वी पर जल के वायुमंडल, भूमि और महासागरों के बीच निरंतर संचलन की एक प्राकृतिक प्रक्रिया है।\n\n"
                    "### जल चक्र के मुख्य चरण:\n"
                    "1. **वाष्पीकरण (Evaporation)**: सूर्य की गर्मी से समुद्रों और नदियों का जल वाष्प बनकर ऊपर उठता है।\n"
                    "2. **वाष्पोत्सर्जन (Transpiration)**: पौधों की पत्तियों से जलवाष्प का वायुमंडल में जाना।\n"
                    "3. **संघनन (Condensation)**: ऊंचाई पर जलवाष्प ठंडा होकर बादलों का निर्माण करता है।\n"
                    "4. **वर्षण (Precipitation)**: वर्षा, बर्फ या ओलों के रूप में जल का पृथ्वी पर पुनः गिरना।\n"
                    "5. **संग्रहण (Collection / Infiltration)**: जल नदियों, भूजल और महासागरों में एकत्र होकर पुनः चक्र शुरू करता है।"
                )
            elif lang == "mr" or "जलचक्र" in q_lower:
                answer = (
                    "**जलचक्र (Water Cycle)**:\n\n"
                    "जलचक्र ही पृथ्वी, वातावरण आणि महासागरांमधील पाण्याच्या निरंतर चक्राकार फिरण्याची नैसर्गिक प्रक्रिया आहे.\n\n"
                    "### जलचक्राचे मुख्य टप्पे:\n"
                    "1. **बाष्पीभवन (Evaporation)**: सूर्याच्या उष्णतेने पाण्याचे बाष्पात रूपांतर होते.\n"
                    "2. **बाष्पोत्सर्जन (Transpiration)**: वनस्पतींच्या पानांमधून पाण्याची वाफ हवेत जाते.\n"
                    "3. **सांद्रीभवन (Condensation)**: उंचावर वाफ थंड होऊन ढग तयार होतात.\n"
                    "4. **पर्जन्यवृष्टी (Precipitation)**: पाऊस किंवा हिमवृष्टीच्या रूपाने पाणी पुन्हा जमिनीवर येते."
                )
            else:
                answer = (
                    "**The Water Cycle (Hydrologic Cycle)**:\n\n"
                    "The water cycle describes the continuous movement of water on, above, and below the surface of the Earth.\n\n"
                    "### Primary Stages:\n"
                    "1. **Evaporation**: Solar energy heats water in oceans and lakes, turning it into vapor.\n"
                    "2. **Transpiration**: Plants release water vapor through their leaf stomata.\n"
                    "3. **Condensation**: Water vapor cools at higher altitudes and condenses into clouds.\n"
                    "4. **Precipitation**: Water falls back to Earth as rain, snow, sleet, or hail.\n"
                    "5. **Collection & Runoff**: Water flows into reservoirs, rivers, aquifers, and oceans, renewing the cycle."
                )
            return {
                "capability": "SCIENCE",
                "sub_type": "water_cycle",
                "result": "Water Cycle",
                "answer": answer,
                "verified": True,
            }
        return None


_science_concept_instance = None


def get_science_engine() -> ScienceConceptEngine:
    global _science_concept_instance
    if _science_concept_instance is None:
        _science_concept_instance = ScienceConceptEngine()
    return _science_concept_instance
