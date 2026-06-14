# Inventory Policy

## Available Inventory

A product is available when status is `available` and quantity is greater than 0.

## Unavailable Inventory

A product is unavailable when status is not `available` or quantity is 0.

## Warehouse Value

Warehouse value is product price multiplied by current quantity across inventory.

## Simulation Inventory

Historical simulations reduce inventory quantities as sales are generated.

When explaining inventory, use product availability, quantity remaining,
warehouse value, and whether simulation changed stock levels when those values
are available in app context.

If a user asks how much inventory is left, answer from app context with total
quantity remaining, available quantity remaining, available product count, and
warehouse value when those values are present.

If a user asks about a specific product, use the matching inventory product row
from app context. Product rows use this structure: `Product name (Category): N
units, price: $X.XX.`
