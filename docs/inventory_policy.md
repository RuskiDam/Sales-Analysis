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
