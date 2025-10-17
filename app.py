import pandas as pd
from typing import Dict, List, Optional, Tuple
import sys

def load_csvs(master_file: str = 'master_inventory.csv', snap_file: str = 'SNAP_inventory_organized.csv') -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Load and return the two CSV files as pandas DataFrames with robust error handling.
    Handles UTF-8-sig encoding and missing files/columns.
    """
    try:
        # Load with explicit encoding for UTF-8-sig
        master_df = pd.read_csv(master_file, encoding='utf-8-sig')
        snap_df = pd.read_csv(snap_file, encoding='utf-8-sig')
        
        # Validate required columns
        required_master_cols = ['ItemID', 'ItemName', 'Category']
        required_snap_cols = ['Item Code', 'Description', 'HCPCS']
        
        if not all(col in master_df.columns for col in required_master_cols):
            raise ValueError(f"Missing required columns in {master_file}: {required_master_cols}")
        if not all(col in snap_df.columns for col in required_snap_cols):
            raise ValueError(f"Missing required columns in {snap_file}: {required_snap_cols}")
        
        print(f"Successfully loaded {len(master_df)} items from master_inventory and {len(snap_df)} from SNAP_inventory.")
        return master_df, snap_df
        
    except FileNotFoundError as e:
        print(f"Error: CSV file not found - {e}. Please ensure files are in the current directory.")
        return None, None
    except pd.errors.EmptyDataError:
        print(f"Error: One or both CSV files are empty.")
        return None, None
    except Exception as e:
        print(f"Unexpected error loading CSVs: {e}")
        return None, None

def find_mask_items(master_df: pd.DataFrame, snap_df: pd.DataFrame, mask_name: str) -> Dict:
    """
    Find items related to the specified mask name and organize them by category.
    Returns a dict with enhanced data including HCPCS.
    """
    if not mask_name or not isinstance(mask_name, str):
        raise ValueError("mask_name must be a non-empty string.")
    
    # Filter for the mask in both CSVs (case-insensitive)
    master_mask = master_df[master_df['ItemName'].str.contains(mask_name, case=False, na=False)]
    snap_mask = snap_df[snap_df['Description'].str.contains(mask_name, case=False, na=False)]
    
    if master_mask.empty and snap_mask.empty:
        return {'error': f"No items found for mask: {mask_name}"}
    
    # Initialize result dictionaries with HCPCS support
    result = {
        'Fitpack': [],
        'Frame': [],
        'Headgear': [],
        'Cushions': {'Small': None, 'Small/Wide': None, 'Medium': None, 'Medium/Wide': None, 
                     'Large': None, 'X-Small': None, 'Wide': None, 'Petite': None, 'Other': []},
        'Summary': "No summary found. This is a general mask report based on available data.",
        'Pros': ["Custom pros not available. Add manually or use web search for details."],
        'Cons': ["Custom cons not available. Add manually or use web search for details."],
        'Alternatives': ["No alternatives found. Suggest similar masks from the inventory."],
        'HCPCS': {}  # Dict to store HCPCS per item type
    }
    
    # Search for Fitpack (kits with multiple sizes or complete systems)
    fitpack = master_mask[master_mask['ItemName'].str.contains('Fitpack|Complete Mask System|Kit', case=False, na=False)]
    for _, row in fitpack.iterrows():
        hcpcs = snap_df[snap_df['Item Code'].str.contains(row['ItemID'], na=False)]['HCPCS'].iloc[0] if not snap_df[snap_df['Item Code'].str.contains(row['ItemID'], na=False)].empty else 'N/A'
        result['Fitpack'].append({'id': row['ItemID'], 'desc': row['ItemName'], 'hcpcs': hcpcs})
        result['HCPCS'][row['ItemID']] = hcpcs
    
    # Search for Frame (mask without headgear)
    frame = snap_mask[snap_mask['Description'].str.contains('Frame System|Mask Only', case=False, na=False)]
    for _, row in frame.iterrows():
        result['Frame'].append({'id': row['Item Code'], 'desc': row['Description'], 'hcpcs': row['HCPCS']})
        result['HCPCS'][row['Item Code']] = row['HCPCS']
    
    # Search for Headgear
    headgear = snap_mask[snap_mask['Description'].str.contains('Headgear|HG', case=False, na=False)]
    for _, row in headgear.iterrows():
        result['Headgear'].append({'id': row['Item Code'], 'desc': row['Description'], 'hcpcs': row['HCPCS']})
        result['HCPCS'][row['Item Code']] = row['HCPCS']
    
    # Search for Cushions (dynamic size matching)
    cushions = snap_mask[snap_mask['Description'].str.contains('Cushion|Pillow|Seal', case=False, na=False)]
    for _, row in cushions.iterrows():
        desc_lower = row['Description'].lower()
        code = row['Item Code']
        full_desc = row['Description']
        hcpcs = row['HCPCS']
        item = {'id': code, 'desc': full_desc, 'hcpcs': hcpcs}
        result['HCPCS'][code] = hcpcs
        
        if 'small wide' in desc_lower or 'sml-wd' in desc_lower or 'sml/wd' in desc_lower:
            result['Cushions']['Small/Wide'] = item
        elif 'medium wide' in desc_lower or 'med-wd' in desc_lower or 'md/wide' in desc_lower:
            result['Cushions']['Medium/Wide'] = item
        elif 'wide' in desc_lower and 'small' not in desc_lower and 'medium' not in desc_lower:
            result['Cushions']['Wide'] = item
        elif 'small' in desc_lower and 'wide' not in desc_lower:
            result['Cushions']['Small'] = item
        elif 'medium' in desc_lower and 'wide' not in desc_lower:
            result['Cushions']['Medium'] = item
        elif 'large' in desc_lower:
            result['Cushions']['Large'] = item
        elif 'x-small' in desc_lower or 'x-sml' in desc_lower or 'xs' in desc_lower:
            result['Cushions']['X-Small'] = item
        elif 'petite' in desc_lower or 'ptt' in desc_lower:
            result['Cushions']['Petite'] = item
        else:
            result['Cushions']['Other'].append(item)
    
    # Generate a basic summary based on category (from master_inventory)
    if not master_mask.empty:
        category = master_mask.iloc[0]['Category']
        result['Summary'] = f"The {mask_name} is a {category} mask. Key features inferred from data: {master_mask.iloc[0]['ItemName']}."
    
    # Find alternatives: Similar masks in the same category (limit to 2)
    if not master_mask.empty:
        category = master_mask.iloc[0]['Category']
        alternatives = master_df[(master_df['Category'] == category) & 
                                (~master_df['ItemName'].str.contains(mask_name, case=False, na=False))].head(2)
        result['Alternatives'] = []
        for _, row in alternatives.iterrows():
            hcpcs = snap_df[snap_df['Item Code'].str.contains(row['ItemID'], na=False)]['HCPCS'].iloc[0] if not snap_df[snap_df['Item Code'].str.contains(row['ItemID'], na=False)].empty else 'N/A'
            result['Alternatives'].append({'id': row['ItemID'], 'desc': row['ItemName'], 'hcpcs': hcpcs})
    
    return result

def generate_ordering_bundle(mask_items: Dict) -> List[Dict]:
    """
    Generate a suggested ordering bundle with common reorder quantities.
    E.g., 3 cushions (for 3-month supply), 1 headgear, 1 frame.
    """
    bundle = []
    
    # Add cushions (prioritize available sizes, qty 3)
    for size, cushion in mask_items['Cushions'].items():
        if cushion and size != 'Other':
            bundle.append({'id': cushion['id'], 'desc': cushion['desc'], 'hcpcs': cushion['hcpcs'], 'qty': 3, 'type': 'Cushion'})
        elif size == 'Other':
            for other in mask_items['Cushions']['Other']:
                bundle.append({'id': other['id'], 'desc': other['desc'], 'hcpcs': other['hcpcs'], 'qty': 3, 'type': 'Cushion'})
    
    # Add headgear (qty 1)
    if mask_items['Headgear']:
        bundle.append({'id': mask_items['Headgear'][0]['id'], 'desc': mask_items['Headgear'][0]['desc'], 
                       'hcpcs': mask_items['Headgear'][0]['hcpcs'], 'qty': 1, 'type': 'Headgear'})
    
    # Add frame (qty 1)
    if mask_items['Frame']:
        bundle.append({'id': mask_items['Frame'][0]['id'], 'desc': mask_items['Frame'][0]['desc'], 
                       'hcpcs': mask_items['Frame'][0]['hcpcs'], 'qty': 1, 'type': 'Frame'})
    
    # Add fitpack if available (qty 1 as starter kit)
    if mask_items['Fitpack']:
        bundle.append({'id': mask_items['Fitpack'][0]['id'], 'desc': mask_items['Fitpack'][0]['desc'], 
                       'hcpcs': mask_items['Fitpack'][0]['hcpcs'], 'qty': 1, 'type': 'Fitpack'})
    
    return bundle

def find_airsense_accessories(master_df: pd.DataFrame, snap_df: pd.DataFrame) -> Dict:
    """Find AirSense A10/A11 accessories (hose, filters, water chamber) with HCPCS."""
    accessories = {'Hose': [], 'Filter': [], 'WaterChamber': []}
    
    # Search master_inventory for AirSense A10/A11 items
    a10_a11 = master_df[master_df['ItemName'].str.contains('A10|A11', case=False, na=False)]
    for _, row in a10_a11.iterrows():
        desc = row['ItemName'].lower()
        item_id = row['ItemID']
        hcpcs = snap_df[snap_df['Item Code'].str.contains(item_id, na=False)]['HCPCS'].iloc[0] if not snap_df[snap_df['Item Code'].str.contains(item_id, na=False)].empty else 'N/A'
        item = {'id': item_id, 'desc': row['ItemName'], 'hcpcs': hcpcs}
        
        if 'tubing' in desc or 'hose' in desc:
            accessories['Hose'].append(item)
        elif 'filter' in desc:
            accessories['Filter'].append(item)
        elif 'humid' in desc or 'water' in desc or 'chamber' in desc:
            accessories['WaterChamber'].append(item)
    
    # Cross-check SNAP_inventory for additional items
    snap_a10_a11 = snap_df[snap_df['Description'].str.contains('AirSense|ClimateLine', case=False, na=False)]
    for _, row in snap_a10_a11.iterrows():
        desc = row['Description'].lower()
        item_code = row['Item Code']
        hcpcs = row['HCPCS']
        item = {'id': item_code, 'desc': row['Description'], 'hcpcs': hcpcs}
        
        if 'tubing' in desc or 'hose' in desc:
            if item not in accessories['Hose']:  # Avoid duplicates
                accessories['Hose'].append(item)
        elif 'filter' in desc:
            if item not in accessories['Filter']:
                accessories['Filter'].append(item)
        elif 'water chamber' in desc or 'humid' in desc or 'chamber' in desc:
            if item not in accessories['WaterChamber']:
                accessories['WaterChamber'].append(item)
    
    return accessories

def format_item_id(item_id: str) -> str:
    """Format Item ID as a clickable/copyable Markdown code block for easy selection."""
    return f"`{item_id}` (click to select/copy)"

def print_mask_report(mask_name: str):
    """Generate and print the report for the specified mask with improved readability and ordering bundle."""
    master_df, snap_df = load_csvs()
    if master_df is None or snap_df is None:
        return
    
    mask_items = find_mask_items(master_df, snap_df, mask_name)
    if 'error' in mask_items:
        print(f"## Error\n{mask_items['error']}")
        return
    
    accessories = find_airsense_accessories(master_df, snap_df)
    bundle = generate_ordering_bundle(mask_items)
    
    # Check if accessories should be displayed (only if mask_name contains 'A11' or 'Airsense A11')
    show_accessories = 'a11' in mask_name.lower() or 'airsense a11' in mask_name.lower()
    
    print(f"# {mask_name} Mask Report 😴\n")
    print("## Associated Items\n")
    
    print("### Fitpack")
    if mask_items['Fitpack']:
        for item in mask_items['Fitpack']:
            print(f"- {format_item_id(item['id'])}: {item['desc']} | HCPCS: {item['hcpcs']}")
    else:
        print("- Not found\n")
    
    print("### Frame Mask")
    if mask_items['Frame']:
        for item in mask_items['Frame']:
            print(f"- {format_item_id(item['id'])}: {item['desc']} | HCPCS: {item['hcpcs']}")
    else:
        print("- Not found\n")
    
    print("### Headgear")
    if mask_items['Headgear']:
        for item in mask_items['Headgear']:
            print(f"- {format_item_id(item['id'])}: {item['desc']} | HCPCS: {item['hcpcs']}")
    else:
        print("- Not found\n")
    
    print("### Cushions")
    has_cushions = False
    for size, cushion in mask_items['Cushions'].items():
        if cushion:
            print(f"- **{size}**: {format_item_id(cushion['id'])}: {cushion['desc']} | HCPCS: {cushion['hcpcs']}")
            has_cushions = True
        elif size == 'Other' and mask_items['Cushions']['Other']:
            for other in mask_items['Cushions']['Other']:
                print(f"- **Other**: {format_item_id(other['id'])}: {other['desc']} | HCPCS: {other['hcpcs']}")
                has_cushions = True
    if not has_cushions:
        print("- No cushions found\n")
    
    # New: Ordering Bundle Section
    print("\n## Suggested Ordering Bundle (3-Month Reorder)")
    if bundle:
        print("| Item ID | Description | HCPCS | Qty | Type |")
        print("|---------|-------------|-------|-----|------|")
        for item in bundle:
            print(f"| {format_item_id(item['id'])} | {item['desc'][:50]}... | {item['hcpcs']} | {item['qty']} | {item['type']} |")
    else:
        print("- No bundle items available.\n")
    
    print("\n## Summary of Mask")
    print(f"{mask_items['Summary']}\n")
    
    print("## Pros")
    for pro in mask_items['Pros']:
        print(f"- {pro}")
    print("")
    
    print("## Cons")
    for con in mask_items['Cons']:
        print(f"- {con}")
    print("")
    
    print("## Best Alternatives")
    for alt in mask_items['Alternatives']:
        print(f"- {format_item_id(alt['id'])}: {alt['desc']} | HCPCS: {alt['hcpcs']}")
    print("")
    
    if show_accessories:
        print("## AirSense A10/A11 Accessories\n")
        print("### Hose/Tubing")
        for item in accessories['Hose']:
            print(f"- {format_item_id(item['id'])}: {item['desc']} | HCPCS: {item['hcpcs']}")
        print("\n### Filters")
        for item in accessories['Filter']:
            print(f"- {format_item_id(item['id'])}: {item['desc']} | HCPCS: {item['hcpcs']}")
        print("\n### Water Chamber")
        for item in accessories['WaterChamber']:
            print(f"- {format_item_id(item['id'])}: {item['desc']} | HCPCS: {item['hcpcs']}")
        print("")
    
    print("*Tip*: Clean your mask cushion daily with mild soap and water! 🧼\n")
    print("For CPAP returns: 5816 E. Shields Ave, Ste 111, Fresno, CA 93727")

# Example usage: Interactive input for versatility
if __name__ == "__main__":
    mask_name = input("Enter the mask name (e.g., AirFit F40): ").strip()
    if not mask_name:
        print("Error: Mask name cannot be empty.")
        sys.exit(1)
    print_mask_report(mask_name)
