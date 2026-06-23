#!/usr/bin/env python3
"""
Load Plan Calculator for Supply Chain Planning
Usage: python load_calculator.py <input.xlsx> <output.xlsx>
"""

import pandas as pd
import math
import sys


def parse_source_data(input_path):
    """
    Parse Excel with non-standard header placement.
    Adjust row indices based on your specific file structure.
    """
    stock_raw = pd.read_excel(input_path, sheet_name='Stock Snapshot', header=None)
    inbounds_raw = pd.read_excel(input_path, sheet_name='Scheduled Inbounds', header=None)
    config_raw = pd.read_excel(input_path, sheet_name='Load Config', header=None)
    
    as_of_date = pd.to_datetime(stock_raw.iloc[0, 1])
    horizon_end = pd.to_datetime(stock_raw.iloc[0, 3])
    
    stock_data = stock_raw.iloc[3:].copy()
    stock_data.columns = ['Item_Code', 'On_Floor_Cases', 'Daily_Sales', '_drop']
    stock_data = stock_data.drop('_drop', axis=1).reset_index(drop=True)
    stock_data['On_Floor_Cases'] = pd.to_numeric(stock_data['On_Floor_Cases'])
    stock_data['Daily_Sales'] = pd.to_numeric(stock_data['Daily_Sales'])
    
    inbounds_data = inbounds_raw.iloc[1:].copy()
    inbounds_data.columns = ['Item_Code', 'Arrival_Date', 'Cases_Due']
    inbounds_data['Arrival_Date'] = pd.to_datetime(inbounds_data['Arrival_Date'])
    inbounds_data['Cases_Due'] = pd.to_numeric(inbounds_data['Cases_Due'])
    
    cases_per_pallet = int(config_raw.iloc[1, 0])
    
    return {
        'as_of_date': as_of_date,
        'horizon_end': horizon_end,
        'stock': stock_data,
        'inbounds': inbounds_data,
        'cases_per_pallet': cases_per_pallet
    }


def calculate_load_plan(data):
    """Execute core load planning calculations."""
    as_of_date = data['as_of_date']
    horizon_end = data['horizon_end']
    planning_days = (horizon_end - as_of_date).days
    
    results = []
    
    for _, row in data['stock'].iterrows():
        item = row['Item_Code']
        on_floor = row['On_Floor_Cases']
        daily_sales = row['Daily_Sales']
        
        current_doh = on_floor / daily_sales if daily_sales > 0 else 999
        projected_oos = as_of_date + pd.DateOffset(days=int(math.floor(current_doh)))
        
        item_inbounds = data['inbounds'][data['inbounds']['Item_Code'] == item]
        inbound_by_horizon = item_inbounds[
            item_inbounds['Arrival_Date'] <= horizon_end
        ]['Cases_Due'].sum()
        
        remaining_demand = daily_sales * planning_days
        additional_needed = max(0, remaining_demand - on_floor - inbound_by_horizon)
        pallets_required = math.ceil(additional_needed / data['cases_per_pallet']) if additional_needed > 0 else 0
        
        required_delivery = projected_oos
        earliest_inbound = item_inbounds['Arrival_Date'].min() if len(item_inbounds) > 0 else None
        earlier_required = required_delivery < earliest_inbound if earliest_inbound else True
        
        results.append({
            'Item_Code': item,
            'On_Floor_Cases': on_floor,
            'Daily_Sales_Cases_Per_Day': daily_sales,
            'Current_Days_On_Hand': current_doh,
            'Projected_OOS_Date': projected_oos,
            'Inbound_Cases_By_Horizon': inbound_by_horizon,
            'Remaining_Demand_Cases': remaining_demand,
            'Additional_Cases_Needed': additional_needed,
            'Pallets_Required': pallets_required,
            'Required_Delivery_Date': required_delivery,
            'Earlier_Delivery_Required': earlier_required
        })
    
    return pd.DataFrame(results)


def main():
    if len(sys.argv) != 3:
        print("Usage: python load_calculator.py <input.xlsx> <output.xlsx>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    data = parse_source_data(input_path)
    load_detail = calculate_load_plan(data)
    action_summary = load_detail[load_detail['Additional_Cases_Needed'] > 0].copy()
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        load_detail.to_excel(writer, sheet_name='Load_Detail', index=False)
        action_summary.to_excel(writer, sheet_name='Load_Action_Summary', index=False)
    
    print(f"Output written to {output_path}")


if __name__ == '__main__':
    main()