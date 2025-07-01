# Configuration Files

This directory contains JSON configuration files for the Agent Tycoon financial simulation system. These files replace hardcoded financial data and allow for easy customization of the simulation parameters.

## Configuration Files

### stocks.json
Defines available stocks and their initial prices.

**Structure:**
```json
{
  "stocks": {
    "TICKER": {
      "ticker": "TICKER",
      "price": "DECIMAL_PRICE"
    }
  }
}
```

**Example:**
```json
{
  "stocks": {
    "AAPL": {
      "ticker": "AAPL",
      "price": "150.00"
    }
  }
}
```

### projects.json
Defines available investment projects with their parameters.

**Structure:**
```json
{
  "projects": [
    {
      "project_id": "PROJECT_ID",
      "name": "PROJECT_NAME",
      "required_investment": "DECIMAL_AMOUNT",
      "expected_return_pct": "DECIMAL_PERCENTAGE",
      "risk_level": "HIGH|MEDIUM|LOW",
      "weeks_to_completion": INTEGER,
      "success_probability": "DECIMAL_PROBABILITY"
    }
  ]
}
```

**Fields:**
- `project_id`: Unique identifier for the project
- `name`: Human-readable project name
- `required_investment`: Total investment amount required (as decimal string)
- `expected_return_pct`: Expected return percentage (0.25 = 25%)
- `risk_level`: Risk category (HIGH, MEDIUM, or LOW)
- `weeks_to_completion`: Duration in weeks
- `success_probability`: Probability of success (0.0 to 1.0)

### bonds.json
Defines available bonds with their characteristics.

**Structure:**
```json
{
  "bonds": [
    {
      "bond_id": "BOND_ID",
      "name": "BOND_NAME",
      "face_value": "DECIMAL_AMOUNT",
      "coupon_rate": "DECIMAL_RATE",
      "maturity_years": INTEGER,
      "current_price": "DECIMAL_PRICE"
    }
  ]
}
```

**Fields:**
- `bond_id`: Unique identifier for the bond
- `name`: Human-readable bond name
- `face_value`: Face value of the bond (typically 1000.00)
- `coupon_rate`: Annual coupon rate (0.025 = 2.5%)
- `maturity_years`: Years until maturity
- `current_price`: Current market price

### market_config.json
Defines market-wide parameters.

**Structure:**
```json
{
  "market_parameters": {
    "base_interest_rate": "DECIMAL_RATE"
  }
}
```

**Fields:**
- `base_interest_rate`: Base interest rate for the market (0.03 = 3%)

## Usage

The configuration system automatically loads these files when the backend classes are initialized. If any configuration file is missing or contains errors, the system will fall back to default hardcoded values and display a warning message.

### Backward Compatibility

The system maintains full backward compatibility:
- If configuration files are missing, default values are used
- If configuration files contain errors, default values are used with error logging
- Existing code continues to work without modification

### Customization

To customize the simulation:
1. Edit the appropriate JSON files in this directory
2. Restart the simulation system
3. The new values will be loaded automatically

**Important Notes:**
- All decimal values should be provided as strings to maintain precision
- Risk levels must be one of: "HIGH", "MEDIUM", "LOW"
- Probabilities should be between 0.0 and 1.0
- All monetary amounts should use decimal notation (e.g., "1000.00")

## Error Handling

The configuration loader includes robust error handling:
- JSON parsing errors are caught and logged
- Missing files trigger warnings but don't break the system
- Invalid data types are handled gracefully
- Default values ensure the system always has valid data

## Testing

When testing with custom configurations:
1. Create test configuration files
2. Pass a custom `ConfigLoader` instance to backend constructors
3. Verify that the system loads your custom data correctly
4. Test fallback behavior by temporarily renaming config files