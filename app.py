import pandas as pd

def load_csvs(master_file='master_inventory.csv', snap_file='SNAP_inventory.csv'):
    """Load and return the two CSV files as pandas DataFrames."""
    try:
        master_df = pd.read_csv(master_file)
        snap_df = pd.read_csv(snap_file)
        return master_df, snap_df
    except FileNotFoundError as e:
        print(f"Error: CSV file not found - {e}")
        return None, None

def find_mask_items(master_df, snap_df, mask_name):
    """Find items related to the specified mask name and organize them by category."""
    # Filter for the mask in both CSVs
    master_mask = master_df[master_df['ItemName'].str.contains(mask_name, case=False, na=False)]
    snap_mask = snap_df[snap_df['Description'].str.contains(mask_name, case=False, na=False)]
    
    # Initialize result dictionaries
    result = {
        'Fitpack': [],
        'Frame': [],
        'Headgear': [],
        'Cushions': {'Small': None, 'Small/Wide': None, 'Medium': None, 'Medium/Wide': None, 'Large': None, 'X-Small': None, 'Wide': None, 'Petite': None, 'Other': []},
        'Summary': "No summary found. This is a general mask report based on available data.",
        'Pros': ["Custom pros not available. Add manually or use web search for details."],
        'Cons': ["Custom cons not available. Add manually or use web search for details."],
        'Alternatives': ["No alternatives found. Suggest similar masks from the inventory."]
    }
    
    # Search for Fitpack (kits with multiple sizes or complete systems)
    fitpack = master_mask[master_mask['ItemName'].str.contains('Fitpack|Complete Mask System|Kit', case=False, na=False)]
    for _, row in fitpack.iterrows():
        result['Fitpack'].append(f"{row['ItemID']}: {row['ItemName']}")
    
    # Search for Frame (mask without headgear)
    frame = snap_mask[snap_mask['Description'].str.contains('Frame System|Mask Only', case=False, na=False)]
    for _, row in frame.iterrows():
        result['Frame'].append(f"{row['Item Code']}: {row['Description']}")
    
    # Search for Headgear
    headgear = snap_mask[snap_mask['Description'].str.contains('Headgear|HG', case=False, na=False)]
    for _, row in headgear.iterrows():
        result['Headgear'].append(f"{row['Item Code']}: {row['Description']}")
    
    # Search for Cushions (dynamic size matching)
    cushions = snap_mask[snap_mask['Description'].str.contains('Cushion|Pillow|Seal', case=False, na=False)]
    for _, row in cushions.iterrows():
        desc_lower = row['Description'].lower()
        code = row['Item Code']
        full_desc = row['Description']
        if 'small wide' in desc_lower or 'sml-wd' in desc_lower or 'sml/wd' in desc_lower:
            result['Cushions']['Small/Wide'] = f"{code}: {full_desc}"
        elif 'medium wide' in desc_lower or 'med-wd' in desc_lower or 'md/wide' in desc_lower:
            result['Cushions']['Medium/Wide'] = f"{code}: {full_desc}"
        elif 'wide' in desc_lower:
            result['Cushions']['Wide'] = f"{code}: {full_desc}"
        elif 'small' in desc_lower:
            result['Cushions']['Small'] = f"{code}: {full_desc}"
        elif 'medium' in desc_lower:
            result['Cushions']['Medium'] = f"{code}: {full_desc}"
        elif 'large' in desc_lower:
            result['Cushions']['Large'] = f"{code}: {full_desc}"
        elif 'x-small' in desc_lower or 'x-sml' in desc_lower or 'xs' in desc_lower:
            result['Cushions']['X-Small'] = f"{code}: {full_desc}"
        elif 'petite' in desc_lower or 'ptt' in desc_lower:
            result['Cushions']['Petite'] = f"{code}: {full_desc}"
        else:
            result['Cushions']['Other'].append(f"{code}: {full_desc}")
    
    # Generate a basic summary based on category (from master_inventory)
    if not master_mask.empty:
        category = master_mask.iloc[0]['Category']
        result['Summary'] = f"The {mask_name} is a {category} mask. Key features inferred from data: {master_mask.iloc[0]['ItemName']}."
    
    # Placeholder for pros/cons/alternatives (can be expanded with more logic or external data)
    # For versatility, you could add web_search integration here if the environment allows
    
    # Find alternatives: Similar masks in the same category
    if not master_mask.empty:
        category = master_mask.iloc[0]['Category']
        alternatives = master_df[(master_df['Category'] == category) & (~master_df['ItemName'].str.contains(mask_name, case=False, na=False))].head(2)
        result['Alternatives'] = []
        for _, row in alternatives.iterrows():
            result['Alternatives'].append(f"{row['ItemID']}: {row['ItemName']}")
    
    return result

def find_airsense_accessories(master_df, snap_df):
    """Find AirSense A10/A11 accessories (hose, filters, water chamber)."""
    accessories = {'Hose': [], 'Filter': [], 'WaterChamber': []}
    
    # Search master_inventory for AirSense A10/A11 items
    a10_a11 = master_df[master_df['ItemName'].str.contains('A10|A11', case=False, na=False)]
    for _, row in a10_a11.iterrows():
        desc = row['ItemName'].lower()
        item_id = row['ItemID']
        if 'tubing' in desc or 'hose' in desc:
            accessories['Hose'].append(f"{item_id}: {row['ItemName']}")
        elif 'filter' in desc:
            accessories['Filter'].append(f"{item_id}: {row['ItemName']}")
        elif 'humid' in desc or 'water' in desc or 'chamber' in desc:
            accessories['WaterChamber'].append(f"{item_id}: {row['ItemName']}")
    
    # Cross-check SNAP_inventory for additional items
    snap_a10_a11 = snap_df[snap_df['Description'].str.contains('AirSense|ClimateLine', case=False, na=False)]
    for _, row in snap_a10_a11.iterrows():
        desc = row['Description'].lower()
        item_code = row['Item Code']
        if 'tubing' in desc or 'hose' in desc:
            accessories['Hose'].append(f"{item_code}: {row['Description']}")
        elif 'filter' in desc:
            accessories['Filter'].append(f"{item_code}: {row['Description']}")
        elif 'water chamber' in desc or 'humid' in desc or 'chamber' in desc:
            accessories['WaterChamber'].append(f"{item_code}: {row['Description']}")
    
    return accessories

def print_mask_report(mask_name):
    """Generate and print the report for the specified mask."""
    master_df, snap_df = load_csvs()
    if master_df is None or snap_df is None:
        return
    
    mask_items = find_mask_items(master_df, snap_df, mask_name)
    accessories = find_airsense_accessories(master_df, snap_df)
    
    print(f"## {mask_name} Mask Report 😴\n")
    
    print("### Associated Items")
    print("\n**Fitpack Item ID**:")
    if mask_items['Fitpack']:
        for fp in mask_items['Fitpack']:
            print(f"- {fp}")
    else:
        print("- Not found")
    print("\n**Frame Mask Item ID**:")
    if mask_items['Frame']:
        for frame in mask_items['Frame']:
            print(f"- {frame}")
    else:
        print("- Not found")
    print("\n**Headgear Item ID**:")
    if mask_items['Headgear']:
        for headgear in mask_items['Headgear']:
            print(f"- {headgear}")
    else:
        print("- Not found")
    print("\n**Cushions**:")
    for size, cushion in mask_items['Cushions'].items():
        if cushion:
            print(f"- {size}: {cushion}")
        elif size == 'Other' and mask_items['Cushions']['Other']:
            for other in mask_items['Cushions']['Other']:
                print(f"- Other: {other}")
    if all(v is None for v in mask_items['Cushions'].values() if v != mask_items['Cushions']['Other']):
        print("- No cushions found")
    
    print("\n### Summary of Mask")
    print(mask_items['Summary'])
    
    print("\n### Pros")
    for pro in mask_items['Pros']:
        print(f"- {pro}")
    
    print("\n### Cons")
    for con in mask_items['Cons']:
        print(f"- {con}")
    
    print("\n### Best Alternative")
    for alt in mask_items['Alternatives']:
        print(f"- {alt}")
    
    print("\n### AirSense A10/A11 Accessories")
    print("\n**Hose/Tubing**:")
    for hose in accessories['Hose']:
        print(f"- {hose}")
    print("\n**Filters**:")
    for filter in accessories['Filter']:
        print(f"- {filter}")
    print("\n**Water Chamber**:")
    for chamber in accessories['WaterChamber']:
        print(f"- {chamber}")
    
    print("\n*Tip*: Clean your mask cushion daily with mild soap and water! 🧼")
    print("\nFor CPAP returns: 5816 E. Shields Ave, Ste 111, Fresno, CA 93727")

# Example usage: Replace 'AirFit F40' with any mask name from the CSVs
if __name__ == "__main__":
    mask_name = input("Enter the mask name (e.g., AirFit F40): ")  # Interactive input for versatility
    print_mask_report(mask_name)