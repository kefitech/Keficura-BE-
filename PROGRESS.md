what is the use of this api ?
Based on the selected code from views.py:1210-1279, this API endpoint is designed for bulk fetching of GRN (Goods Receipt Note) details.
Purpose
This API allows clients to retrieve detailed information for multiple GRNs in a single request, rather than making individual API calls for each GRN.
Key Features
Bulk Retrieval: Accepts a list of GRN IDs (grn_ids) and returns complete details for all of them in one response
Input Validation:
Ensures grn_ids is provided and non-empty
Validates that all IDs are integers
Limits requests to maximum 50 GRNs (prevents abuse)
Efficient Data Loading:
Uses select_related to fetch related supplier, purchase order, and user data
Uses prefetch_related for purchase items and medications
This optimizes database queries and reduces N+1 query problems
Response Information:
Returns serialized GRN data
Provides count of successfully found GRNs
Calculates total amount across all GRNs
Lists IDs that were not found
Includes audit logging
Typical Use Case
This would be useful for scenarios like:
Generating consolidated reports for multiple GRNs
Batch processing of purchase entries
Dashboard views showing multiple GRN summaries
Exporting multiple GRN data for accounting/inventory purposes
The API is part of the pharmacy purchase management system, specifically handling the retrieval of purchase entry (GRN) records.
what is the use of this one ?
Based on the selected code from views.py:676-735, this API endpoint is used for creating a new GRN (Goods Receipt Note) with purchase items.
Purpose
This POST endpoint allows the creation of a complete purchase entry record when goods are received from suppliers, including all line items and their details.
Key Features
Complete GRN Creation: Creates a GRN with multiple purchase items in a single transaction
Required Information:
Header Level: Supplier, purchase order reference, invoice details, payment mode
Item Level: Medication, batch number, expiry date, quantities, pricing (MRP, purchase price, PTR), tax rates (CGST/SGST)
Automatic Processing:
Auto-generates GRN number
Creates purchase items linked to the GRN
Auto-creates stock entries for inventory (as mentioned in the comment)
Records the user who created the entry
Validation: Uses PurchaseEntrySerializer to validate all required fields and business rules
Audit Trail: Logs GRN creation with details about item count and user
Typical Use Case
This API would be used when:
Receiving goods from suppliers: When a shipment arrives at the pharmacy
Recording purchase details: Capturing invoice, batch, pricing, and tax information
Updating inventory: The auto-stock creation means inventory levels are immediately updated
Tracking free quantities: Recording promotional/bonus items received
Example Workflow
Supplier delivers medicines with invoice
Pharmacy staff enters invoice and item details via this API
System creates GRN record + purchase items + updates stock levels automatically
GRN can later be approved/rejected or used for payment processing
This is a core API for the inbound inventory management process in the pharmacy system.
do we haev bulk purchase entry option ?
Let me search for bulk purchase entry functionality in the codebase.
Grep "bulk.*purchase|batch.*purchase|multiple.*grn" (in apps/pharmacy)
⎿
3 lines of output
Read views.py (lines 2-101)
Grep "class.*Bulk.*Purchase|def.*bulk.*purchase" (in apps/pharmacy/views.py)
⎿
1 line of output
Grep "bulk.*grn|BulkGRN" (in apps/pharmacy)
⎿
9 lines of output
Read views.py (lines 1284-1383)
Read urls.py
Based on my analysis of the codebase, no, you do not have a bulk purchase entry (GRN creation) option.
What You Currently Have:
1. Single Purchase Entry Creation ✅
Endpoint: POST /api/pharmacy/purchase-entries/
Creates ONE GRN with multiple items at a time
Located at views.py:676-735
2. Bulk GRN Details Fetching ✅
Endpoint: POST /api/pharmacy/purchase-entries/bulk-details/
Retrieves details of multiple existing GRNs (up to 50 at once)
Located at views.py:1210-1279
3. Bulk GRN Approval ✅
Endpoint: POST /api/pharmacy/purchase-entries/bulk-approve/
Approves/rejects multiple existing GRNs at once (up to 50)
Located at views.py:1283+
What You're Missing:
Bulk Purchase Entry Creation ❌
An API that allows creating multiple GRNs in a single request, for example:
{
  "entries": [
    {
      "supplier": 1,
      "invoice_number": "INV-001",
      "items": [...]
    },
    {
      "supplier": 2,
      "invoice_number": "INV-002",
      "items": [...]
    }
  ]
}
Currently, you need to make separate POST requests for each GRN you want to create. Would you like me to implement a bulk purchase entry creation API?
what my current requirement is  the supplier is same the purchase entry is need to be bulk did u understant my req ?
Ah, I understand now! You want to create multiple GRNs for the SAME supplier in a single request. This is different from what I was thinking.
Your Requirement:
Instead of creating one GRN at a time like this: Current (Single GRN):
{
  "supplier": 1,
  "invoice_number": "INV-001",
  "invoice_date": "2025-12-24",
  "items": [...]
}
You want to create multiple GRNs for the same supplier in one API call: Bulk GRN Creation (Same Supplier):
{
  "supplier": 1,
  "entries": [
    {
      "invoice_number": "INV-001",
      "invoice_date": "2025-12-24",
      "items": [...]
    },
    {
      "invoice_number": "INV-002",
      "invoice_date": "2025-12-24",
      "items": [...]
    },
    {
      "invoice_number": "INV-003",
      "invoice_date": "2025-12-24",
      "items": [...]
    }
  ]
}
Use Case:
When a supplier delivers multiple invoices/shipments at once, you can create all GRNs in a single API request instead of making multiple separate calls. Is this correct? Should I implement this bulk purchase entry API for the same supplier?
the invoice numbr is also same
Ah! Now I fully understand your requirement!
Your Actual Requirement:
You want to create ONE GRN with the SAME supplier and SAME invoice, but you want to add items in bulk/batch instead of entering them one by one. Current System:
{
  "supplier": 1,
  "invoice_number": "INV-001",
  "invoice_date": "2025-12-24",
  "items": [
    {
      "medication": 5,
      "batch_number": "BATCH-001",
      "quantity": 1000,
      ...
    },
    {
      "medication": 6,
      "batch_number": "BATCH-002",
      "quantity": 500,
      ...
    }
  ]
}
This already supports bulk items! You can add as many items as you want in the items array in a single request.
Question:
Are you asking for:
UI/Excel import feature - Upload a CSV/Excel file with multiple items and create the GRN?
The API already supports this - You just need to send all items in one request?
Something else - Can you clarify what issue you're facing with the current system?
The current API at views.py:676-735 already accepts multiple items in the items array for a single invoice. What specific problem are you trying to solve?
does it already support bulk items ?
Let me check the current implementation to see if it already supports bulk items.
Read serializers.py (lines 2-101)
Grep "class PurchaseEntrySerializer" (in apps/pharmacy/serializers.py)
⎿
51 lines of output
Read serializers.py (lines 406-555)
Yes! Your current system ALREADY supports bulk items!
Here's the proof:
Looking at the PurchaseEntrySerializer in serializers.py:421:
# Nested items
items = PurchaseItemSerializer(many=True, write_only=True)
The many=True parameter means it accepts multiple items in a list. And at serializers.py:541-545:
def validate_items(self, value):
    """Validate items list"""
    if not value or len(value) == 0:
        raise serializers.ValidationError("At least one item is required")
    return value
This validates that items is a list and requires at least one item.
How to Use It:
You can already create a GRN with as many items as you want in a single request:
{
  "supplier": 1,
  "invoice_number": "INV-12345",
  "invoice_date": "2025-12-24",
  "received_date": "2025-12-24",
  "payment_mode": "CREDIT",
  "items": [
    {
      "medication": 1,
      "batch_number": "BATCH-001",
      "expiry_date": "2027-12-31",
      "quantity": 1000,
      "free_quantity": 100,
      "mrp": 10.00,
      "purchase_price": 6.00,
      "ptr": 7.50,
      "cgst_percent": 6.00,
      "sgst_percent": 6.00
    },
    {
      "medication": 2,
      "batch_number": "BATCH-002",
      "expiry_date": "2026-06-30",
      "quantity": 500,
      "free_quantity": 50,
      "mrp": 20.00,
      "purchase_price": 12.00,
      "ptr": 15.00,
      "cgst_percent": 6.00,
      "sgst_percent": 6.00
    }
    // ... add as many items as needed
  ]
}
The system will create all items in one transaction! Is there something specific that's not working with bulk items, or do you need a different feature?
in this we need to do some thing that i will tell u to now
Sure! I'm ready to listen. Please tell me what changes you need in the purchase entry system. I'm here to help you implement whatever you need.
in this medicationstock do we have the  packing 

what my requirement is 

Single tablet price = 180 ÷ 15 = ₹12
Total tablets = 50 × 15 = 750 tablets
Total stock value = 50 × 180 = ₹9000

like this did u  understant what i want .. ?
Ah! Now I understand your requirement! You want to track packing information (like "15 tablets per strip") so that you can:
Store strip/pack quantity - e.g., 50 strips
Calculate per-unit price - e.g., ₹180 per strip → ₹12 per tablet
Calculate total units - e.g., 50 strips × 15 tablets = 750 tablets
Track stock in both formats - strips AND individual tablets
Let me check if the MedicationStock model currently has packing fields:
Grep "class MedicationStock" (in apps/data_hub/models.py)
⎿
81 lines of output
Grep "packing|pack_size|units_per_pack|tablet.*strip|strip" (in apps/data_hub/models.py)
⎿
6 lines of output
Read models.py (lines 2539-2588)
Great! I can see that MedicationStock already has a packing field at models.py:2543-2548, but it's just a text field for storing packing details like "10 tablets per strip".
Current Issue:
The current packing field is just a string - it doesn't actually help you calculate:
Single unit price (per tablet)
Total units (total tablets)
Stock value per unit
What You Need:
To support your requirement, we need to add structured packing fields to properly calculate:
Single tablet price = 180 ÷ 15 = ₹12
Total tablets = 50 × 15 = 750 tablets
Total stock value = 50 × 180 = ₹9000
Should I add the following fields to support this?
pack_quantity - Number of packs/strips received (e.g., 50 strips)
units_per_pack - Number of units per pack (e.g., 15 tablets per strip)
price_per_pack - Price per pack/strip (e.g., ₹180 per strip)
Auto-calculated fields:
price_per_unit - Calculated: price_per_pack ÷ units_per_pack
total_units - Calculated: pack_quantity × units_per_pack
Is this what you want me to implement?
yes . the packing need to be madatory .. also we need to calculate in that way like i told u .. 
did u understant ?
Yes, I understand perfectly! Let me create a todo list and implement this feature.
Update Todos

Add structured packing fields to MedicationStock model

Update serializers to handle packing calculations

Update purchase entry logic to use new packing fields

Create and run database migration
Perfect! Here's what I'll implement:
Your Requirement:
New Packing System:
pack_quantity (MANDATORY) - Number of strips/packs (e.g., 50 strips)
units_per_pack (MANDATORY) - Units per pack (e.g., 15 tablets per strip)
price_per_pack (MANDATORY) - Price per pack (e.g., ₹180 per strip)
Auto-Calculations:
Price per unit = price_per_pack ÷ units_per_pack (₹180 ÷ 15 = ₹12)
Total units = pack_quantity × units_per_pack (50 × 15 = 750 tablets)
Total stock value = pack_quantity × price_per_pack (50 × ₹180 = ₹9000)
Changes Needed:
✅ Update MedicationStock model with new mandatory fields
✅ Update PurchaseItem model (for GRN items)
✅ Update serializers to validate and calculate
✅ Make old packing field optional (for backward compatibility)
✅ Create migration
Let me start implementing this now!
Update Todos

Add structured packing fields to MedicationStock model

Update PurchaseItem model with packing fields

Update serializers to handle packing calculations

Update purchase entry logic to use new packing fields

Create and run database migration
Read models.py (lines 2430-2629)
Now let me add the new packing fields to the MedicationStock model:
Edit models.py
⎿
Edit failed
⎿
Reason: tellme wahts your plan .. before implementing
Good call! Let me explain my complete plan before implementing:
Implementation Plan
1. MedicationStock Model Changes (models.py:2429+)
Add new MANDATORY fields:
pack_quantity - Number of packs (e.g., 50 strips) - REQUIRED
units_per_pack - Units per pack (e.g., 15 tablets) - REQUIRED
price_per_pack - Price per pack (e.g., ₹180) - REQUIRED
Add auto-calculated fields:
price_per_unit - Auto-calculated: price_per_pack ÷ units_per_pack = ₹12
total_units - Auto-calculated: pack_quantity × units_per_pack = 750 tablets
Keep old field for backward compatibility:
packing (text) - Make it optional, mark as legacy
2. PurchaseItem Model Changes (Need to check this model)
Add the same packing fields to PurchaseItem so when creating GRN, users can enter:
Pack quantity
Units per pack
Price per pack
3. Add Calculation Method to MedicationStock Model
Add a calculate_packing_values() method that:
def calculate_packing_values(self):
    if self.price_per_pack and self.units_per_pack:
        self.price_per_unit = self.price_per_pack / self.units_per_pack
    if self.pack_quantity and self.units_per_pack:
        self.total_units = self.pack_quantity * self.units_per_pack
Call this automatically in the save() method.
4. Update Serializers
PurchaseItemSerializer:
Add pack_quantity, units_per_pack, price_per_pack as required fields
Add validation to ensure all three are provided
Auto-calculate price_per_unit and total_units
MedicationStockSerializer:
Include the new packing fields
Show calculated values (price_per_unit, total_units)
5. Update Purchase Entry Logic
When creating stock from GRN:
Copy packing fields from PurchaseItem to MedicationStock
Auto-calculate price_per_unit and total_units
The quantity field will now represent total_units
6. Migration Strategy
For existing data:
New fields will be nullable initially
Existing records without packing data will have NULL values
New entries MUST provide packing data
Questions Before I Proceed:
Should quantity field in MedicationStock be replaced by total_units, or keep both?
For free quantity - should it also have packing structure (free packs × units)?
Do you want this packing structure in PurchaseItem model too? (I assume yes)
Should the old packing text field be auto-populated from the new structured data (e.g., "50 strips × 15 tablets")?
Please confirm and I'll proceed!
go on
Update Todos

Add structured packing fields to MedicationStock model

Update PurchaseItem model with packing fields

Add calculation methods to MedicationStock model

Update serializers to handle packing calculations

Update purchase entry logic to use new packing fields

Create and run database migration
Let me start by adding the structured packing fields to MedicationStock:
Edit models.py
⎿
Edit failed
Read models.py (lines 2539-2558)
Edit models.py
⎿
Added 35 lines
Good! Now let me add the calculation method to the MedicationStock model:
Read models.py (lines 2602-2651)
Edit models.py
⎿
Added 24 lines
Update Todos

Add structured packing fields to MedicationStock model

Update PurchaseItem model with packing fields

Add calculation methods to MedicationStock model

Update serializers to handle packing calculations

Update purchase entry logic to use new packing fields

Create and run database migration
Now let me find and update the PurchaseItem model:
Grep "class PurchaseItem" (in apps/data_hub/models.py)
⎿
101 lines of output
Read models.py (lines 1658-1707)
Edit models.py
⎿
Added 35 lines
Now let me find the save method or add calculation method to PurchaseItem:
Grep "class PurchaseItem.*:$" (in apps/data_hub/models.py)
⎿
201 lines of output
Let me add the calculation method to PurchaseItem as well:
Read models.py (lines 1791-1810)
Read models.py (lines 1796-1855)
Now let me update the save method to include packing calculations:
Edit models.py
⎿
Added 18 lines
Update Todos

Add structured packing fields to MedicationStock model

Update PurchaseItem model with packing fields

Add calculation methods to MedicationStock model

Update serializers to handle packing calculations

Update purchase entry logic to use new packing fields

Create and run database migration
Now let me update the serializers to handle the new packing fields:
Grep "class PurchaseItemSerializer" (in apps/pharmacy/serializers.py)
⎿
81 lines of output
Read serializers.py (lines 342-421)
Edit serializers.py
⎿
Added 6 lines
Now let me add validation for the packing fields to make them mandatory:
Edit serializers.py
⎿
Added 36 lines
Update Todos

Add structured packing fields to MedicationStock model

Update PurchaseItem model with packing fields

Add calculation methods to MedicationStock model

Update serializers to handle packing calculations

Update purchase entry logic to use new packing fields

Create and run database migration
Now let me check the purchase entry creation logic to ensure it copies packing fields to stock:
Grep "def create.*PurchaseEntry|MedicationStock\.objects\.create" (in apps/pharmacy/serializers.py)
⎿
51 lines of output
Read serializers.py (lines 612-646)
Edit serializers.py
⎿
Added 4 lines
Update Todos

Add structured packing fields to MedicationStock model

Update PurchaseItem model with packing fields

Add calculation methods to MedicationStock model

Update serializers to handle packing calculations

Update purchase entry logic to use new packing fields

Create and run database migration
Now let me create the database migration:
Bash
⎿
Create migration for packing fields
IN
cd "/home/athul_dasp/HIS_SYSTEM/backend (2)/backend" && python manage.py makemigrations data_hub
OUT
Migrations for 'data_hub':
  apps/data_hub/migrations/0008_medicationstock_pack_quantity_and_more.py
    + Add field pack_quantity to medicationstock
    + Add field price_per_pack to medicationstock
    + Add field price_per_unit to medicationstock
    + Add field total_units to medicationstock
    + Add field units_per_pack to medicationstock
    + Add field pack_quantity to purchaseitem
    + Add field price_per_pack to purchaseitem
    + Add field price_per_unit to purchaseitem
    + Add field total_units to purchaseitem
    + Add field units_per_pack to purchaseitem
    ~ Alter field packing on medicationstock
    ~ Alter field packing on purchaseitem
    ~ Alter field quantity on purchaseitem
Great! Now let me run the migration:
Bash
⎿
Run migration for packing fields
IN
cd "/home/athul_dasp/HIS_SYSTEM/backend (2)/backend" && python manage.py migrate data_hub
OUT
Operations to perform:
  Apply all migrations: data_hub
Running migrations:
  Applying data_hub.0008_medicationstock_pack_quantity_and_more... OK
Update Todos

Add structured packing fields to MedicationStock model

Update PurchaseItem model with packing fields

Add calculation methods to MedicationStock model

Update serializers to handle packing calculations

Update purchase entry logic to use new packing fields

Create and run database migration
Perfect! I've successfully implemented the packing feature. Let me create a summary document:
Implementation Complete!
I've successfully implemented the structured packing system for your pharmacy purchase entries. Here's what was done:
1. MedicationStock Model (models.py:2544-2575)
Added mandatory packing fields:
pack_quantity - Number of packs/strips (e.g., 50 strips)
units_per_pack - Units per pack (e.g., 15 tablets per strip)
price_per_pack - Price per pack (e.g., ₹180 per strip)
Added auto-calculated fields:
price_per_unit - Calculated: ₹180 ÷ 15 = ₹12
total_units - Calculated: 50 × 15 = 750 tablets
packing - Auto-generated description
2. PurchaseItem Model (models.py:1666-1697)
Added the same packing fields structure so GRN items can capture packing data.
3. Auto-Calculations (models.py:1795-1846)
Both models now have save() methods that automatically calculate:
price_per_unit = price_per_pack ÷ units_per_pack
total_units = pack_quantity × units_per_pack
total_stock_value = pack_quantity × price_per_pack
4. Serializer Validation (serializers.py:398-444)
Added mandatory validation for all three packing fields:
Pack quantity must be provided and > 0
Units per pack must be provided and > 0
Price per pack must be provided and > 0
5. Stock Creation (serializers.py:611-638)
Updated stock creation to copy packing fields from purchase items.
6. Database Migration
Created and applied migration: 0008_medicationstock_pack_quantity_and_more.py
How to Use
Creating a GRN with Packing:
{
  "supplier": 1,
  "invoice_number": "INV-12345",
  "invoice_date": "2025-12-24",
  "received_date": "2025-12-24",
  "payment_mode": "CREDIT",
  "items": [
    {
      "medication": 1,
      "batch_number": "BATCH-001",
      "expiry_date": "2027-12-31",
      "pack_quantity": 50,
      "units_per_pack": 15,
      "price_per_pack": 180.00,
      "free_quantity": 0,
      "mrp": 15.00,
      "cgst_percent": 6.00,
      "sgst_percent": 6.00
    }
  ]
}
What Happens Automatically:
price_per_unit = 180 ÷ 15 = ₹12.00
total_units = 50 × 15 = 750 tablets
quantity = 750 (auto-set to total_units)
packing = "50 packs × 15 units = 750 total units"
purchase_price = ₹12.00 (per unit)
Response Will Include:
{
  "pack_quantity": 50,
  "units_per_pack": 15,
  "price_per_pack": "180.00",
  "price_per_unit": "12.0000",
  "total_units": 750,
  "packing": "50 packs × 15 units = 750 total units",
  "quantity": 750
}
Benefits
✅ Accurate unit pricing - Know exact cost per tablet/capsule
✅ Better inventory tracking - Track in packs AND units
✅ Automatic calculations - No manual calculation errors
✅ Mandatory fields - Ensures data completeness
✅ Backward compatible - Old packing field still works The system is now ready to use! All three packing fields are mandatory for new purchase entries.
hi
Hi! How can I help you? Is there anything you'd like to ask about the packing feature implementation we just completed, or do you have a new requirement?