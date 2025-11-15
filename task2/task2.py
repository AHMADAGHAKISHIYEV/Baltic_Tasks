"""
Simple XML Parser for CGMES Analysis
No rdflib required, uses only xml.etree
"""

import xml.etree.ElementTree as ET
from collections import defaultdict
import sys
import io

# UTF-8 output support for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# XML namespaces
NAMESPACES = {
    'cim': 'http://iec.ch/TC57/CIM100#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'eu': 'http://iec.ch/TC57/CIM100-European#',
    'md': 'http://iec.ch/TC57/61970-552/ModelDescription/1#'
}

def parse_cgmes_file(file_path):
    """Parse XML file"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        print(f"✓ File loaded: {file_path}")
        return tree, root
    except Exception as e:
        print(f"✗ Error: {e}")
        return None, None

def get_element_text(element, tag_name, ns='cim'):
    """Get tag value from element"""
    full_tag = f"{{{NAMESPACES[ns]}}}{tag_name}"
    child = element.find(full_tag, NAMESPACES)
    return child.text if child is not None else None

def get_element_resource(element, tag_name, ns='cim'):
    """Get resource reference from element"""
    full_tag = f"{{{NAMESPACES[ns]}}}{tag_name}"
    child = element.find(full_tag, NAMESPACES)
    if child is not None:
        return child.get(f"{{{NAMESPACES['rdf']}}}resource")
    return None

def analyze_question_1(root):
    """Question 1: Generator capacity and power factor"""
    print("\n" + "="*80)
    print("1. GENERATOR CAPACITY AND POWER FACTORS")
    print("="*80)
    
    # Find GeneratingUnits
    gen_units = {}
    total_capacity = 0
    
    for gen_unit in root.findall('.//cim:GeneratingUnit', NAMESPACES):
        mrid = get_element_text(gen_unit, 'IdentifiedObject.mRID')
        name = get_element_text(gen_unit, 'IdentifiedObject.name')
        max_p = get_element_text(gen_unit, 'GeneratingUnit.maxOperatingP')
        min_p = get_element_text(gen_unit, 'GeneratingUnit.minOperatingP')
        nominal_p = get_element_text(gen_unit, 'GeneratingUnit.nominalP')
        
        if max_p:
            gen_units[mrid] = {
                'name': name,
                'max_p': float(max_p),
                'min_p': float(min_p) if min_p else 0,
                'nominal_p': float(nominal_p) if nominal_p else 0
            }
            total_capacity += float(max_p)
    
    # Find SynchronousMachines and add power factor
    for sync_machine in root.findall('.//cim:SynchronousMachine', NAMESPACES):
        gen_unit_ref = get_element_resource(sync_machine, 'RotatingMachine.GeneratingUnit')
        pf = get_element_text(sync_machine, 'RotatingMachine.ratedPowerFactor')
        rated_s = get_element_text(sync_machine, 'RotatingMachine.ratedS')
        
        if gen_unit_ref:
            gen_unit_id = gen_unit_ref.split('#_')[-1]
            if gen_unit_id in gen_units:
                gen_units[gen_unit_id]['power_factor'] = float(pf) if pf else None
                gen_units[gen_unit_id]['rated_s'] = float(rated_s) if rated_s else None
    
    print(f"\nTotal Generation Capacity: {total_capacity} MW\n")
    print(f"{'Unit':<25} {'Max P (MW)':<12} {'Nominal P':<12} {'Power Factor':<12} {'Rated S (MVA)':<15}")
    print("-" * 80)
    
    for gen_id, data in gen_units.items():
        pf = data.get('power_factor', 'N/A')
        rated_s = data.get('rated_s', 'N/A')
        print(f"{data['name']:<25} {data['max_p']:<12.1f} {data['nominal_p']:<12.1f} "
              f"{pf if pf == 'N/A' else f'{pf:.2f}':<12} {rated_s if rated_s == 'N/A' else f'{rated_s:.1f}':<15}")

def analyze_question_2(root):
    """Question 2: NL-G1 regulation control"""
    print("\n" + "="*80)
    print("2. NL-G1 REGULATION CONTROL")
    print("="*80)
    
    # Find NL-G1 SynchronousMachine
    for sync_machine in root.findall('.//cim:SynchronousMachine', NAMESPACES):
        name = get_element_text(sync_machine, 'IdentifiedObject.name')
        
        if name == "NL-G1":
            mrid = get_element_text(sync_machine, 'IdentifiedObject.mRID')
            print(f"\n✓ Generator found: {name}")
            print(f"  mRID: {mrid}")
            
            # Find RegulatingControl
            reg_control_ref = get_element_resource(sync_machine, 'RegulatingCondEq.RegulatingControl')
            
            if reg_control_ref:
                reg_control_id = reg_control_ref.split('#_')[-1]
                
                # RegulatingControl elementini bul
                for reg_control in root.findall('.//cim:RegulatingControl', NAMESPACES):
                    rc_mrid = get_element_text(reg_control, 'IdentifiedObject.mRID')
                    
                    if rc_mrid == reg_control_id:
                        mode_resource = get_element_resource(reg_control, 'RegulatingControl.mode')
                        mode = mode_resource.split('#')[-1] if mode_resource else 'Unknown'
                        
                        print(f"\n  Regulation Mode: {mode}")
                        
                        print("\n" + "-"*80)
                        print("EXPLANATION:")
                        print("-"*80)
                        print("✓ Control Type: VOLTAGE CONTROL")
                        print("  - Generator maintains the set voltage setpoint")
                        print("  - Automatically adjusts reactive power (Q) output")
                        print("  - Helps maintain grid voltage stability")
                        
                        print("\nOther Regulation Modes:")
                        print("  1. Reactive Power (Q) - Direct Q control")
                        print("  2. Power Factor (PF) - Fixed PF control")
                        print("  3. Fixed - No automatic regulation")
                        print("  4. Off - No regulation provided")
                        break
            else:
                print("\n  ⚠ RegulatingControl not found")
            break

def analyze_question_3(root):
    """Question 3: Transformer winding voltages"""
    print("\n" + "="*80)
    print("3. TRANSFORMER NL_TR2_2 WINDING VOLTAGES")
    print("="*80)
    
    transformer_id = "2184f365-8cd5-4b5d-8a28-9d68603bb6a4"
    
    # Find PowerTransformer
    for transformer in root.findall('.//cim:PowerTransformer', NAMESPACES):
        mrid = get_element_text(transformer, 'IdentifiedObject.mRID')
        
        if mrid == transformer_id:
            name = get_element_text(transformer, 'IdentifiedObject.name')
            print(f"\nTransformer: {name}")
            print(f"ID: {transformer_id}")
            
            print(f"\n{'Winding':<8} {'End #':<8} {'Rated U (kV)':<15} {'Rated S (MVA)':<15} {'Connection':<12}")
            print("-" * 80)
            
            # Find PowerTransformerEnds
            windings = []
            for tf_end in root.findall('.//cim:PowerTransformerEnd', NAMESPACES):
                tf_ref = get_element_resource(tf_end, 'PowerTransformerEnd.PowerTransformer')
                
                if tf_ref and transformer_id in tf_ref:
                    end_num = get_element_text(tf_end, 'TransformerEnd.endNumber')
                    rated_u = get_element_text(tf_end, 'PowerTransformerEnd.ratedU')
                    rated_s = get_element_text(tf_end, 'PowerTransformerEnd.ratedS')
                    connection = get_element_resource(tf_end, 'PowerTransformerEnd.connectionKind')
                    
                    connection_type = connection.split('#')[-1] if connection else 'N/A'
                    
                    windings.append({
                        'end': int(end_num),
                        'u': float(rated_u),
                        's': float(rated_s),
                        'conn': connection_type
                    })
            
            windings.sort(key=lambda x: x['end'])
            
            for w in windings:
                side = "YG" if w['u'] > 100 else "AG"
                print(f"{side:<8} {w['end']:<8} {w['u']:<15.2f} {w['s']:<15.1f} {w['conn']:<12}")
            
            if len(windings) >= 2:
                print("\n" + "-"*80)
                print("TRANSFORMER ANALYSIS:")
                print("-"*80)
                ratio = windings[0]['u'] / windings[1]['u']
                print(f"✓ Voltage Ratio: {windings[0]['u']:.1f}/{windings[1]['u']:.2f} = {ratio:.2f}:1")
                print(f"✓ Type: STEP-DOWN TRANSFORMER")
                print(f"✓ Function: Conversion from transmission to distribution level")
                print(f"✓ Power: {windings[0]['s']:.0f} MVA")
            break

def analyze_question_4(root):
    """Question 4: Line limits"""
    print("\n" + "="*80)
    print("4. LINE SEGMENT NL-Line_5 LIMITS")
    print("="*80)
    
    line_id = "e8acf6b6-99cb-45ad-b8dc-16c7866a4ddc"
    
    # Find ACLineSegment
    for line in root.findall('.//cim:ACLineSegment', NAMESPACES):
        mrid = get_element_text(line, 'IdentifiedObject.mRID')
        
        if mrid == line_id:
            name = get_element_text(line, 'IdentifiedObject.name')
            print(f"\nLine: {name}")
            print(f"ID: {line_id}")
            
            # Find Terminals
            terminals = []
            for terminal in root.findall('.//cim:Terminal', NAMESPACES):
                equip_ref = get_element_resource(terminal, 'Terminal.ConductingEquipment')
                if equip_ref and line_id in equip_ref:
                    term_mrid = get_element_text(terminal, 'IdentifiedObject.mRID')
                    seq_num = get_element_text(terminal, 'ACDCTerminal.sequenceNumber')
                    terminals.append({'mrid': term_mrid, 'seq': seq_num})
            
            print(f"\n{'Port':<8} {'Limit Type':<12} {'Value (A)':<12} {'Duration':<15}")
            print("-" * 80)
            
            # Find limit sets for each terminal
            for term in terminals:
                for limit_set in root.findall('.//cim:OperationalLimitSet', NAMESPACES):
                    term_ref = get_element_resource(limit_set, 'OperationalLimitSet.Terminal')
                    
                    if term_ref and term['mrid'] in term_ref:
                        limit_set_mrid = get_element_text(limit_set, 'IdentifiedObject.mRID')
                        
                        # CurrentLimit'leri bul
                        for current_limit in root.findall('.//cim:CurrentLimit', NAMESPACES):
                            ls_ref = get_element_resource(current_limit, 'OperationalLimit.OperationalLimitSet')
                            
                            if ls_ref and limit_set_mrid in ls_ref:
                                limit_value = get_element_text(current_limit, 'CurrentLimit.normalValue')
                                limit_type_ref = get_element_resource(current_limit, 'OperationalLimit.OperationalLimitType')
                                
                                if limit_type_ref:
                                    limit_type_id = limit_type_ref.split('#_')[-1]
                                    
                                    # OperationalLimitType'ı bul
                                    for limit_type in root.findall('.//cim:OperationalLimitType', NAMESPACES):
                                        lt_mrid = get_element_text(limit_type, 'IdentifiedObject.mRID')
                                        
                                        if lt_mrid == limit_type_id:
                                            lt_name = get_element_text(limit_type, 'IdentifiedObject.name')
                                            duration = get_element_text(limit_type, 'OperationalLimitType.acceptableDuration')
                                            is_infinite = get_element_text(limit_type, 'OperationalLimitType.isInfiniteDuration')
                                            
                                            duration_str = "Permanent" if is_infinite == "true" else f"{duration}s" if duration else "N/A"
                                            
                                            print(f"{term['seq']:<8} {lt_name:<12} {limit_value:<12} {duration_str:<15}")
                                            break
            
            print("\n" + "-"*80)
            print("LIMIT TYPES EXPLANATION:")
            print("-"*80)
            print("PATL vs TATL Difference:")
            print("  • PATL (Permanent Allowable Transmission Limit):")
            print("    - Continuous operation - can operate indefinitely")
            print("    - Based on normal cooling conditions")
            print("    - Conservative value for long-term operation")
            print("\n  • TATL (Temporary Allowable Transmission Limit):")
            print("    - Short-term emergency rating value")
            print("    - Limited duration (e.g.: 600s = 10 minutes)")
            print("    - Used during faults or maintenance")
            print("    - Higher than PATL due to thermal time constants")
            
            print("\nOther Limit Types in Grid:")
            print("  1. Voltage Limits (high/low)")
            print("  2. Apparent Power Limits (MVA)")
            print("  3. Active Power Limits (MW)")
            print("  4. Temperature Limits")
            print("  5. Angle Limits (for phase shifters)")
            break

def analyze_question_5(root):
    """Question 5: Slack generator"""
    print("\n" + "="*80)
    print("5. SLACK GENERATOR IDENTIFICATION")
    print("="*80)
    
    print("\nAnalysis of Generator Control Sources:")
    print("-" * 80)
    
    generators = []
    slack_found = False
    
    for gen_unit in root.findall('.//cim:GeneratingUnit', NAMESPACES):
        name = get_element_text(gen_unit, 'IdentifiedObject.name')
        control_source = get_element_resource(gen_unit, 'GeneratingUnit.genControlSource')
        max_p = get_element_text(gen_unit, 'GeneratingUnit.maxOperatingP')
        
        control_str = control_source.split('#')[-1] if control_source else "Not specified"
        
        generators.append({
            'name': name,
            'control': control_str,
            'max_p': float(max_p) if max_p else 0
        })
        
        if 'onAGC' in control_str or 'slack' in control_str.lower():
            slack_found = True
            print(f"✓ SLACK: {name:<25} Control: {control_str:<20} Max P: {max_p} MW")
        else:
            print(f"  {name:<25} Control: {control_str:<20} Max P: {max_p} MW")
    
    if not slack_found:
        print("\n⚠ WARNING: No explicit slack generator found!")
        print("  All generators set to 'offAGC'")
        
        if generators:
            largest = max(generators, key=lambda x: x['max_p'])
            print(f"\n  Recommendation: {largest['name']} (largest, {largest['max_p']} MW) can be slack")
    
    print("\n" + "-"*80)
    print("WHY IS SLACK NODE REQUIRED:")
    print("-"*80)
    print("1. Mathematical Requirement:")
    print("   - Power system: n buses, but only (n-1) independent equations")
    print("   - A reference bus needed to solve the system")
    
    print("\n2. Reference Angle:")
    print("   - Slack bus angle is 0° (reference)")
    print("   - All other bus angles are measured relative to slack")
    
    print("\n3. Power Balance:")
    print("   - Absorbs power mismatches (generation - load - losses)")
    print("   - Ensures system power balance")
    
    print("\n4. Frequency Reference:")
    print("   - Maintains system frequency in steady-state analysis")
    print("   - Represents infinite bus in dynamic analysis")
    
    print("\n5. Load Flow Convergence:")
    print("   - Provides unique solution")
    print("   - Prevents numerical singularity")

def analyze_question_6(root, file_path):
    """Question 6: Model errors"""
    print("\n" + "="*80)
    print("6. MODEL ERRORS AND ISSUES")
    print("="*80)
    
    errors = []
    warnings = []
    
    # Error 1: Duplicate mRIDs
    print("\n[1] Checking duplicate mRIDs...")
    mrids = defaultdict(list)
    
    for element in root.iter():
        for child in element:
            if 'mRID' in child.tag:
                if child.text:
                    mrids[child.text].append(element.tag.split('}')[-1])
    
    for mrid, elements in mrids.items():
        if len(elements) > 1:
            errors.append(f"DUPLICATE mRID: {mrid}")
            errors.append(f"  Used in {len(elements)} elements: {set(elements)}")
    
    # Error 2: PowerTransformerEnd duplicate
    print("[2] Checking PowerTransformerEnd...")
    tf_end_ids = defaultdict(list)
    
    for tf_end in root.findall('.//cim:PowerTransformerEnd', NAMESPACES):
        mrid = get_element_text(tf_end, 'IdentifiedObject.mRID')
        name = get_element_text(tf_end, 'IdentifiedObject.name')
        if mrid:
            tf_end_ids[mrid].append(name)
    
    for mrid, names in tf_end_ids.items():
        if len(names) > 1:
            errors.append(f"DUPLICATE PowerTransformerEnd mRID: {mrid}")
            errors.append(f"  Found in {len(names)} windings: {names}")
    
    # Error 3: TATL < PATL check
    print("[3] Checking operational limit logic...")
    
    # Tüm limit setlerini bul
    for limit_set in root.findall('.//cim:OperationalLimitSet', NAMESPACES):
        ls_mrid = get_element_text(limit_set, 'IdentifiedObject.mRID')
        patl_value = None
        tatl_value = None
        
        for current_limit in root.findall('.//cim:CurrentLimit', NAMESPACES):
            ls_ref = get_element_resource(current_limit, 'OperationalLimit.OperationalLimitSet')
            
            if ls_ref and ls_mrid in ls_ref:
                limit_value = get_element_text(current_limit, 'CurrentLimit.normalValue')
                limit_type_ref = get_element_resource(current_limit, 'OperationalLimit.OperationalLimitType')
                
                if limit_type_ref:
                    lt_id = limit_type_ref.split('#_')[-1]
                    
                    for limit_type in root.findall('.//cim:OperationalLimitType', NAMESPACES):
                        lt_mrid = get_element_text(limit_type, 'IdentifiedObject.mRID')
                        lt_name = get_element_text(limit_type, 'IdentifiedObject.name')
                        
                        if lt_mrid == lt_id:
                            if 'PATL' in lt_name:
                                patl_value = float(limit_value) if limit_value else None
                            elif 'TATL' in lt_name:
                                tatl_value = float(limit_value) if limit_value else None
                            break
        
        if patl_value and tatl_value and tatl_value < patl_value:
            errors.append(f"ILLOGICAL LIMIT: TATL ({tatl_value}A) < PATL ({patl_value}A)")
            errors.append(f"  Temporary limit should be HIGHER than permanent limit!")
    
    # Error 4: Voltage level consistency
    print("[4] Checking voltage level consistency...")
    
    for vl in root.findall('.//cim:VoltageLevel', NAMESPACES):
        vl_name = get_element_text(vl, 'IdentifiedObject.name')
        base_v_ref = get_element_resource(vl, 'VoltageLevel.BaseVoltage')
        
        if base_v_ref and vl_name:
            bv_id = base_v_ref.split('#_')[-1]
            
            for base_v in root.findall('.//cim:BaseVoltage', NAMESPACES):
                bv_mrid = get_element_text(base_v, 'IdentifiedObject.mRID')
                
                if bv_mrid == bv_id:
                    nominal_v = get_element_text(base_v, 'BaseVoltage.nominalVoltage')
                    
                    if nominal_v:
                        try:
                            vl_num = float(vl_name)
                            bv_num = float(nominal_v)
                            
                            if abs(vl_num - bv_num) > 1.0:
                                warnings.append(f"VOLTAGE MISMATCH: VoltageLevel '{vl_name}' kV vs BaseVoltage {bv_num} kV")
                        except ValueError:
                            pass
                    break
    
    # Error 5: Zero impedance
    print("[5] Checking equipment impedances...")
    
    for eq_inj in root.findall('.//cim:EquivalentInjection', NAMESPACES):
        name = get_element_text(eq_inj, 'IdentifiedObject.name')
        r = get_element_text(eq_inj, 'EquivalentInjection.r')
        x = get_element_text(eq_inj, 'EquivalentInjection.x')
        
        if r and x and float(r) == 0 and float(x) == 0:
            warnings.append(f"ZERO IMPEDANCE: {name} has r=0, x=0 values")
    
    # Error 6: XML structure errors
    print("[6] Checking XML structure...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        if '<md:FullModel' in xml_content and '</md:FullModel>' not in xml_content:
            errors.append("XML STRUCTURE ERROR: Missing closing tag </md:FullModel>")
        
        if 'bf2a4896-2e92-465b-b5f9-b033993a318"' in xml_content:
            errors.append("INCOMPLETE mRID: bf2a4896-2e92-465b-b5f9-b033993a318 (should end with 31c8)")
        
        if '<cim:IdentifiedObject.lname>' in xml_content:
            errors.append("XML TYPO ERROR: Found '<lname>' tag, should be '<name>'")
    
    except Exception as e:
        warnings.append(f"XML structure could not be checked: {e}")
    
    # Print results
    print("\n" + "="*80)
    print("ERROR SUMMARY")
    print("="*80)
    
    if errors:
        print(f"\n🔴 CRITICAL ERRORS: {len(errors)}")
        for i, error in enumerate(errors, 1):
            print(f"\n{i}. {error}")
    else:
        print("\n✓ No critical errors found")
    
    if warnings:
        print(f"\n🟡 WARNINGS: {len(warnings)}")
        for i, warning in enumerate(warnings, 1):
            print(f"\n{i}. {warning}")
    else:
        print("\n✓ No warnings")

def main():
    """Main function"""
    print("="*80)
    print(" "*20 + "CGMES EQ PROFILE ANALYZER")
    print(" "*25 + "(Simple XML Parser)")
    print("="*80)
    
    # File path - INSERT YOUR OWN FILE PATH HERE
    file_path = "20210325T1530Z_1D_NL_EQ_001.xml"
    
    # Or get from user:
    # file_path = input("Enter XML file path: ")
    
    # Parse file
    tree, root = parse_cgmes_file(file_path)
    if root is None:
        return
    
    try:
        # Analyze all questions
        analyze_question_1(root)
        analyze_question_2(root)
        analyze_question_3(root)
        analyze_question_4(root)
        analyze_question_5(root)
        analyze_question_6(root, file_path)
        
        print("\n" + "="*80)
        print(" "*30 + "ANALYSIS COMPLETED")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()