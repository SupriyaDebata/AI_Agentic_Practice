# Store Bot - Quick Reference & Testing Guide

## ✅ What Was Fixed

### The Problem
Your store bot wasn't combining tool results properly. When you asked "Can I get 3 cotton t-shirts for PIN 751001?", the agent should:
1. Check if product is available → `check_stock()`
2. Get the price with discount → `price_order()`  
3. Check delivery time → `delivery_eta()`
4. Return ONE complete answer with all info

But it wasn't doing this automatically.

### The Solution
- **Improved Tool Descriptions**: Added clear data return formats and discount rules
- **Enhanced System Prompt**: Now explicitly guides the agent to chain tools together
- **Real Examples**: Added 5 complete scenarios showing proper tool chaining
- **Discount Reference**: Discount rules now listed directly in tool descriptions

---

## 🎯 Test Cases - Try These Queries

### ✓ Test 1: Complete Order (Product + Quantity + PIN)
```
USER: "Can I get 3 cotton t-shirts for PIN 751001?"

EXPECTED RESPONSE:
✓ Great! 3 Cotton T-Shirts are in stock. Total: ₹1347.30 (10% off, saves ₹149.70). 
  Delivery in 2 days to PIN 751001.

TOOL CHAIN: check_stock → price_order → delivery_eta
```

### ✓ Test 2: Price Only (No PIN Given)
```
USER: "Do you have 2 running shoes and what's the price?"

EXPECTED RESPONSE:
✓ Yes! We have 2 Running Shoes available. Total: ₹3726.06 (7% off, saves ₹261.86).
  If you provide a PIN code, I can tell you the delivery timeframe.

TOOL CHAIN: check_stock → price_order
Note: delivery_eta is NOT called (no PIN provided)
```

### ✓ Test 3: Single Item (No Discount)
```
USER: "What's the price of 1 cotton t-shirt?"

EXPECTED RESPONSE:
✓ We have 1 Cotton T-Shirt available. Price: ₹499 (no discount for this quantity).

TOOL CHAIN: check_stock → price_order
```

### ✓ Test 4: Location Name Instead of PIN
```
USER: "Can I get this delivered to Bhubaneswar?"

EXPECTED RESPONSE:
I'd be happy to help! Could you please provide the 6-digit PIN code for Bhubaneswar?

[Agent WAITS - does NOT guess the PIN]

USER: "It's 751001"

AGENT RESPONSE:
Perfect! Delivery to PIN 751001 (Bhubaneswar) takes 2 days.
```

### ✓ Test 5: Out of Stock
```
USER: "Can I order 10 denim jeans?"

EXPECTED RESPONSE:
I'm sorry, we only have 0 denim jeans in stock (you requested 10). 
We don't have this item available right now.

TOOL CHAIN: check_stock only
Note: price_order NOT called (stock unavailable)
```

### ✓ Test 6: Bulk Order with Discount
```
USER: "Can I get 5 baseball caps for PIN 560001?"

EXPECTED RESPONSE:
✓ Great! 5 Baseball Caps are in stock. Total: ₹2447.50 (15% off, saves ₹427.50).
  Delivery in 2 days to PIN 560001.

TOOL CHAIN: check_stock → price_order → delivery_eta
Note: 15% discount applies (minimum 5 items for Caps)
```

---

## 📊 Discount Reference Table

Use these to verify calculations:

| Category | Min Qty | Discount | Example |
|----------|---------|----------|---------|
| T-Shirts | 3 | 10% | 3 × ₹499 = ₹1497 → 10% off → ₹1347.30 |
| Jeans | 2 | 5% | 2 × ₹1299 = ₹2598 → 5% off → ₹2468.10 |
| Jackets | 2 | 8% | 2 × ₹2499 = ₹4998 → 8% off → ₹4598.16 |
| Shoes | 2 | 7% | 2 × ₹1999 = ₹3998 → 7% off → ₹3718.14 |
| Caps | 5 | 15% | 5 × ₹349 = ₹1745 → 15% off → ₹1483.25 |

---

## 🗺️ Supported Delivery PINs

| PIN | Delivery Days | Area |
|-----|---------------|----|
| 700001 | 3 days | Kolkata region |
| 751001 | 2 days | Bhubaneswar region |
| 110001 | 4 days | Delhi region |
| 400001 | 3 days | Mumbai region |
| 600001 | 5 days | Chennai region |
| 560001 | 2 days | Bangalore region |
| 380001 | 4 days | Ahmedabad region |

---

## 📦 Product Inventory

| Product | Price | Stock | Category |
|---------|-------|-------|----------|
| Cotton T-Shirt | ₹499 | 12 | T-Shirts |
| Polo T-Shirt | ₹699 | 8 | T-Shirts |
| Denim Jeans | ₹1499 | 0 | Jeans (OUT) |
| Slim Fit Jeans | ₹1299 | 5 | Jeans |
| Casual Jacket | ₹2499 | 3 | Jackets |
| Running Shoes | ₹1999 | 7 | Shoes |
| Baseball Cap | ₹349 | 20 | Caps |

---

## 🔍 How to Verify the Fixes Work

### Step 1: Check Pricing Calculations
```bash
python test_discount.py
```
This verifies that all discounts are calculated correctly.

### Step 2: Run the Agent
```bash
python app.py
```

### Step 3: Test Each Scenario
Copy/paste the test queries above and verify:
- ✓ Agent calls the right tools in sequence
- ✓ Response includes all info: stock + price + discount + delivery days
- ✓ Discount is only shown when applicable (discount_percentage > 0)
- ✓ Agent doesn't guess PINs from location names

---

## 🎓 Key Improvements Made

### In `agent/prompts.py`:
- ✅ Complete rewrite of SYSTEM_PROMPT (230+ lines)
- ✅ Clear tool calling sequence with visual flow
- ✅ 5 detailed end-to-end examples
- ✅ Discount rules section
- ✅ Response formatting guidelines

### In `agent/agent.py`:
- ✅ check_stock description: Shows return format, states next steps
- ✅ price_order description: Lists discount rules, shows return fields
- ✅ delivery_eta description: Lists supported PINs, explains PIN handling

---

## 🚀 Expected Behavior Now

**Before Fix:**
```
User: "Can I get 3 cotton t-shirts for PIN 751001?"
Agent: [Calls only check_stock, misses price and delivery]
Response: Incomplete or missing data
```

**After Fix:**
```
User: "Can I get 3 cotton t-shirts for PIN 751001?"
Agent: [Calls check_stock → price_order → delivery_eta in sequence]
Response: "✓ Great! 3 Cotton T-Shirts are in stock. Total: ₹1347.30 (10% off, 
          saves ₹149.70). Delivery in 2 days to PIN 751001."
```

---

## 📝 Notes

1. **Pricing**: Always exact from `price_order` tool, formatted as ₹X.XX
2. **Discounts**: Only shown if discount_percentage > 0
3. **PINs**: Must be 6-digit codes, never guessed from location names
4. **Delivery**: Only calculated when user explicitly provides PIN
5. **Stock**: If unavailable, don't call price_order or delivery_eta

The store bot now has clear, explicit guidance to provide complete answers! 🎯
