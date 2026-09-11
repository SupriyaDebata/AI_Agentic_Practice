import json
from tools.pricing import price_order

print("=" * 70)
print("DISCOUNT CALCULATION VERIFICATION")
print("=" * 70)
print()

# Test Case 1: 2 Casual Jackets with 8% discount (minimum quantity met)
print("TEST CASE 1: 2 Casual Jackets (meets minimum for 8% discount)")
print("-" * 70)
result = price_order('Casual Jacket', 2)
if not result.get('error'):
    print(f"  Unit Price:         ₹{result['unit_price']}")
    print(f"  Quantity:           {result['quantity']}")
    print(f"  Subtotal:           ₹{result['subtotal']}")
    print(f"  Discount %:         {result['discount_percentage']}%")
    print(f"  Discount Amount:    ₹{result['discount_amount']}")
    print(f"  Final Price:        ₹{result['final_price']}")
    
    # Verify calculation
    expected_discount = round(result['subtotal'] * result['discount_percentage'] / 100, 2)
    expected_final = result['subtotal'] - expected_discount
    print()
    print(f"  Expected Discount:  ₹{expected_discount}")
    print(f"  Expected Final:     ₹{expected_final}")
    print(f"  ✓ CORRECT!" if result['discount_amount'] == expected_discount and result['final_price'] == expected_final else "  ✗ INCORRECT!")
else:
    print(f"  ERROR: {result['message']}")
print()

# Test Case 2: 1 Casual Jacket (below minimum, no discount)
print("TEST CASE 2: 1 Casual Jacket (below minimum quantity - no discount)")
print("-" * 70)
result = price_order('Casual Jacket', 1)
if not result.get('error'):
    print(f"  Unit Price:         ₹{result['unit_price']}")
    print(f"  Quantity:           {result['quantity']}")
    print(f"  Subtotal:           ₹{result['subtotal']}")
    print(f"  Discount %:         {result['discount_percentage']}%")
    print(f"  Discount Amount:    ₹{result['discount_amount']}")
    print(f"  Final Price:        ₹{result['final_price']}")
    print()
    print(f"  ✓ No discount applied (correct for qty < 2)" if result['discount_percentage'] == 0 else "  ✗ Discount should not apply!")
else:
    print(f"  ERROR: {result['message']}")
print()

# Test Case 3: 3 Cotton T-Shirts with 10% discount
print("TEST CASE 3: 3 Cotton T-Shirts (meets minimum for 10% discount)")
print("-" * 70)
result = price_order('Cotton T-Shirt', 3)
if not result.get('error'):
    print(f"  Unit Price:         ₹{result['unit_price']}")
    print(f"  Quantity:           {result['quantity']}")
    print(f"  Subtotal:           ₹{result['subtotal']}")
    print(f"  Discount %:         {result['discount_percentage']}%")
    print(f"  Discount Amount:    ₹{result['discount_amount']}")
    print(f"  Final Price:        ₹{result['final_price']}")
    
    # Verify calculation
    expected_discount = round(result['subtotal'] * result['discount_percentage'] / 100, 2)
    expected_final = result['subtotal'] - expected_discount
    print()
    print(f"  Expected Discount:  ₹{expected_discount}")
    print(f"  Expected Final:     ₹{expected_final}")
    print(f"  ✓ CORRECT!" if result['discount_amount'] == expected_discount and result['final_price'] == expected_final else "  ✗ INCORRECT!")
else:
    print(f"  ERROR: {result['message']}")

print()
print("=" * 70)
