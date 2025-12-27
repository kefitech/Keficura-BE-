from rest_framework import serializers
from apps.data_hub.models import *
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone


# ============================================================================
# SUPPLIER SERIALIZERS
# ============================================================================

class SupplierSerializer(serializers.ModelSerializer):
    """
    Supplier Serializer

    Handles serialization and validation for Supplier model.
    Auto-generates supplier code if not provided.

    Features:
        - Auto-generate supplier code (SUP-0001, SUP-0002, etc.)
        - Validate GSTIN uniqueness
        - Validate phone number format
        - Display choice field labels
        - Read-only fields for audit data
        - Returns medications_stock mapping for supplier returns
    """

    # Display fields for choice values
    supplier_type_display = serializers.CharField(source='get_supplier_type_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    rating_display = serializers.CharField(source='get_rating_display', read_only=True)

    # Read-only fields
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True)

    # Medications and stock mapping from this supplier
    medications_stock = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = [
            'id', 'code', 'name', 'supplier_type', 'supplier_type_display',
            'contact_person', 'phone', 'alternate_phone', 'email', 'address',
            'gstin', 'pan', 'drug_license_number',
            'payment_type', 'payment_type_display', 'credit_days', 'credit_limit',
            'bank_name', 'account_number', 'ifsc_code',
            'rating', 'rating_display',
            'is_active', 'comments',
            'created_by_name', 'created_on', 'updated_by_name', 'updated_on',
            'medications_stock'
        ]
        read_only_fields = ['id', 'code', 'created_on', 'updated_on', 'created_by_name', 'updated_by_name', 'medications_stock']

    def get_medications_stock(self, obj):
        """
        Get all medication_id and stock_id pairs from this supplier
        Returns list of {medication_id, stock_id} for items with current stock > 0
        """
        # Get all purchase entries from this supplier
 

        # Get stock entries linked to this supplier via purchase_entry
        stock_entries = MedicationStock.objects.filter(
            purchase_entry__supplier=obj,
            is_active=True
        ).values('medication_id', 'id').distinct()

        return [
            {
                'medication_id': entry['medication_id'],
                'stock_id': entry['id']
            }
            for entry in stock_entries
        ]

    def validate_phone(self, value):
        """Validate phone number format"""
        if value:
            # Remove spaces and special characters
            cleaned = ''.join(filter(str.isdigit, value))
            if len(cleaned) < 10:
                raise serializers.ValidationError("Phone number must be at least 10 digits")
        return value

    def validate_gstin(self, value):
        """Validate GSTIN format and uniqueness"""
        # Convert empty string to None to avoid unique constraint issues
        if not value or value.strip() == '':
            return None

        # GSTIN format: 15 characters
        if len(value) != 15:
            raise serializers.ValidationError("GSTIN must be exactly 15 characters")

        # Check uniqueness (excluding current instance during update)
        query = Supplier.objects.filter(gstin=value)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)

        if query.exists():
            raise serializers.ValidationError("A supplier with this GSTIN already exists")

        return value

    def validate_credit_days(self, value):
        """Validate credit days is non-negative"""
        if value < 0:
            raise serializers.ValidationError("Credit days cannot be negative")
        return value

    def validate_credit_limit(self, value):
        """Validate credit limit is positive if provided"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Credit limit cannot be negative")
        return value

    def validate(self, data):
        """
        Cross-field validation
        - If payment_type is CREDIT, credit_days should be > 0
        - If payment_type is CASH, credit_days should be 0
        - Convert empty strings to None for optional fields
        """
        # Convert empty strings to None for fields that might be empty
        optional_fields = ['email', 'alternate_phone', 'pan', 'drug_license_number',
                          'bank_name', 'account_number', 'ifsc_code']

        for field in optional_fields:
            if field in data and (not data[field] or data[field].strip() == ''):
                data[field] = None

        payment_type = data.get('payment_type', self.instance.payment_type if self.instance else None)
        credit_days = data.get('credit_days', self.instance.credit_days if self.instance else 0)

        if payment_type == 'CASH' and credit_days > 0:
            raise serializers.ValidationError({
                "credit_days": "Credit days must be 0 for cash-only suppliers"
            })

        if payment_type == 'CREDIT' and credit_days == 0:
            raise serializers.ValidationError({
                "credit_days": "Credit days must be greater than 0 for credit suppliers"
            })

        return data


class SupplierListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing suppliers
    Used in dropdown selections and list views
    Returns medications_stock for supplier returns management
    """
    supplier_type_display = serializers.CharField(source='get_supplier_type_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)

    # Medications and stock mapping from this supplier
    medications_stock = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = [
            'id', 'code', 'name', 'supplier_type', 'supplier_type_display',
            'phone', 'email', 'payment_type', 'payment_type_display',
            'credit_days', 'is_active', 'medications_stock', 'rating', 'contact_person',
            'alternate_phone', 'address', 'gstin', 'pan', 'drug_license_number',
            'bank_name', 'account_number', 'ifsc_code', 'credit_limit'
        ]

    def get_medications_stock(self, obj):
        """
        Get all medication_id and stock_id pairs from this supplier
        Returns list of {medication_id, stock_id} for active stock entries
        """

        # Get stock entries linked to this supplier via purchase_entry
        stock_entries = MedicationStock.objects.filter(
            purchase_entry__supplier=obj,
            is_active=True
        ).values('medication_id', 'id').distinct()

        return [
            {
                'medication_id': entry['medication_id'],
                'stock_id': entry['id']
            }
            for entry in stock_entries
        ]
        


# ============================================================================
# PURCHASE ORDER SERIALIZERS
# ============================================================================

class PurchaseOrderSerializer(serializers.ModelSerializer):
    """
    Purchase Order Serializer

    Handles serialization and validation for PurchaseOrder model.
    Auto-generates PO number if not provided.

    Features:
        - Auto-generate PO number (PO-YYYYMMDD-XXXX)
        - Validate supplier exists and is active
        - Validate dates (expected_delivery >= order_date)
        - Display supplier details
        - Display status labels
        - Calculate received amount from linked GRNs
        - Accept both 'supplier' and 'supplier_id' in requests
    """

    # Display fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    supplier_code = serializers.CharField(source='supplier.code', read_only=True)

    # Additional info
    received_amount = serializers.SerializerMethodField(read_only=True)
    pending_amount = serializers.SerializerMethodField(read_only=True)
    grn_count = serializers.SerializerMethodField(read_only=True)

    # Audit fields
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'supplier_name', 'supplier_code',
            'order_date', 'expected_delivery_date',
            'status', 'status_display', 'total_amount',
            'received_amount', 'pending_amount', 'grn_count',
            'notes', 'is_active', 'comments',
            'created_by_name', 'created_on', 'updated_by_name', 'updated_on'
        ]
        read_only_fields = ['id', 'po_number', 'created_on', 'updated_on']

    def to_internal_value(self, data):
        """
        Allow both 'supplier' and 'supplier_id' field names.
        If 'supplier_id' is provided, map it to 'supplier'.
        """
        # Create a mutable copy of the data
        data_copy = data.copy() if hasattr(data, 'copy') else dict(data)

        # If supplier_id is provided but not supplier, use supplier_id
        if 'supplier_id' in data_copy and 'supplier' not in data_copy:
            data_copy['supplier'] = data_copy.pop('supplier_id')

        return super().to_internal_value(data_copy)

    def get_received_amount(self, obj):
        """Get total amount received from linked GRNs"""
        try:
            return str(obj.get_received_amount())
        except AttributeError:
            # GRN functionality not implemented yet
            return "0.00"

    def get_pending_amount(self, obj):
        """Calculate pending amount"""
        try:
            received = obj.get_received_amount()
            pending = obj.total_amount - received
            return str(max(pending, 0))
        except AttributeError:
            # GRN functionality not implemented yet
            return str(obj.total_amount)

    def get_grn_count(self, obj):
        """Count linked GRNs"""
        try:
            return obj.purchase_entries.filter(is_active=True).count()
        except AttributeError:
            # GRN functionality not implemented yet
            return 0

    def validate_supplier(self, value):
        """Validate supplier exists and is active"""
        if not value.is_active:
            raise serializers.ValidationError("Supplier is not active")
        return value

    def validate_total_amount(self, value):
        """Validate total amount is non-negative"""
        if value < 0:
            raise serializers.ValidationError("Total amount cannot be negative")
        return value

    def validate(self, data):
        """
        Cross-field validation
        - expected_delivery_date should be >= order_date
        """
        order_date = data.get('order_date', self.instance.order_date if self.instance else None)
        expected_delivery = data.get('expected_delivery_date',
                                    self.instance.expected_delivery_date if self.instance else None)

        if expected_delivery and order_date:
            if expected_delivery < order_date:
                raise serializers.ValidationError({
                    "expected_delivery_date": "Expected delivery date cannot be before order date"
                })

        return data


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing purchase orders
    Used in list views and dropdown selections
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    supplier_code = serializers.CharField(source='supplier.code', read_only=True)
    grn_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier_name', 'supplier_code',
            'order_date', 'expected_delivery_date',
            'status', 'status_display', 'total_amount', 'grn_count'
        ]

    def get_grn_count(self, obj):
        """Count linked GRNs"""
        try:
            return obj.purchase_entries.filter(is_active=True).count()
        except AttributeError:
            # GRN functionality not implemented yet
            return 0


# ============================================================================
# PURCHASE ENTRY (GRN) SERIALIZERS
# ============================================================================

class PurchaseItemSerializer(serializers.ModelSerializer):
    """
    Purchase Item Serializer

    Handles line items in a GRN with auto-calculations.

    Features:
        - Auto-calculate tax amount from GST percentages
        - Auto-calculate margin from MRP and purchase price
        - Auto-calculate total amount
        - Validate expiry date
        - Display medication details
    """

    # Display fields
    medication_name = serializers.CharField(source='medication.name', read_only=True)
    medication_dosage = serializers.CharField(source='medication.dosage_form', read_only=True)

    # Calculated fields (read-only, auto-calculated on save)
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    margin_percent = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    # NEW: Packing calculated fields (read-only)
    price_per_unit = serializers.DecimalField(max_digits=10, decimal_places=4, read_only=True)
    total_units = serializers.IntegerField(read_only=True)

    class Meta:
        model = PurchaseItem
        fields = [
            'id', 'medication', 'medication_name', 'medication_dosage',
            'batch_number', 'expiry_date',
            'quantity', 'free_quantity',
            'pack_quantity', 'units_per_pack', 'price_per_pack', 'price_per_unit', 'total_units',
            'packing',
            'mrp', 'purchase_price', 'ptr',
            'discount_percent', 'discount_amount',
            'cgst_percent', 'sgst_percent', 'igst_percent', 'tax_amount',
            'total_amount', 'margin_percent',
            'stock_entry'
        ]
        read_only_fields = ['id', 'tax_amount', 'total_amount', 'margin_percent', 'discount_amount', 'stock_entry', 'price_per_unit', 'total_units', 'packing']

    def validate_quantity(self, value):
        """Validate quantity is positive"""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value

    def validate_expiry_date(self, value):
        """Validate expiry date is in future"""
        from datetime import date
        if value < date.today():
            raise serializers.ValidationError("Expiry date cannot be in the past")
        return value

    def validate(self, data):
        """Cross-field validation"""
        # NEW: Validate packing fields are mandatory
        pack_quantity = data.get('pack_quantity')
        units_per_pack = data.get('units_per_pack')
        price_per_pack = data.get('price_per_pack')

        if not pack_quantity:
            raise serializers.ValidationError({
                "pack_quantity": "Pack quantity is mandatory (e.g., 50 strips)"
            })

        if not units_per_pack:
            raise serializers.ValidationError({
                "units_per_pack": "Units per pack is mandatory (e.g., 15 tablets per strip)"
            })

        if not price_per_pack:
            raise serializers.ValidationError({
                "price_per_pack": "Price per pack is mandatory (e.g., ₹180 per strip)"
            })

        # Validate packing fields are positive
        if pack_quantity <= 0:
            raise serializers.ValidationError({
                "pack_quantity": "Pack quantity must be greater than 0"
            })

        if units_per_pack <= 0:
            raise serializers.ValidationError({
                "units_per_pack": "Units per pack must be greater than 0"
            })

        if price_per_pack <= 0:
            raise serializers.ValidationError({
                "price_per_pack": "Price per pack must be greater than 0"
            })

        mrp = data.get('mrp', 0)
        purchase_price = data.get('purchase_price', 0)

        if purchase_price > mrp:
            raise serializers.ValidationError({
                "purchase_price": "Purchase price cannot be greater than MRP"
            })

        return data


class PurchaseEntrySerializer(serializers.ModelSerializer):
    """
    Purchase Entry (GRN) Serializer

    Handles GRN creation with nested items.

    Features:
        - Nested PurchaseItem creation
        - Auto-generate GRN number
        - Auto-calculate totals from items
        - Create MedicationStock for each item
        - Update PurchaseOrder status
        - Validate all business rules
    """

    # Nested items
    items = PurchaseItemSerializer(many=True, write_only=True)
    purchase_items = PurchaseItemSerializer(many=True, read_only=True)

    # Display fields
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    supplier_code = serializers.CharField(source='supplier.code', read_only=True)
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True, allow_null=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    payment_mode_display = serializers.CharField(source='get_payment_mode_display', read_only=True)

    # Additional info
    items_count = serializers.SerializerMethodField(read_only=True)
    calculation_summary = serializers.SerializerMethodField(read_only=True)

    # Audit fields
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True)

    # Approval workflow display fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)

    class Meta:
        model = PurchaseEntry
        fields = [
            'id', 'grn_number', 'supplier', 'supplier_name', 'supplier_code',
            'purchase_order', 'po_number',
            'invoice_number', 'invoice_date', 'received_date',
            'subtotal', 'discount_amount', 'tax_amount', 'total_amount',
            'payment_status', 'payment_status_display',
            'payment_mode', 'payment_mode_display', 'payment_date',
            'status', 'status_display', 'approved_by', 'approved_by_name', 'approved_date', 'stock_created',
            'notes', 'is_active', 'comments',
            'items', 'purchase_items', 'items_count', 'calculation_summary',
            'created_by_name', 'created_on', 'updated_by_name', 'updated_on'
        ]
        read_only_fields = ['id', 'grn_number', 'subtotal', 'tax_amount', 'total_amount', 'status', 'approved_by', 'approved_date', 'stock_created', 'created_on', 'updated_on']

    def get_items_count(self, obj):
        """Count items in GRN"""
        return obj.purchase_items.count()

    def get_calculation_summary(self, obj):
        """
        Generate detailed calculation breakdown for the GRN
        Shows how total_amount is calculated from all items
        """
        from decimal import Decimal

        items_breakdown = []
        total_base_amount = Decimal('0.00')
        total_discount = Decimal('0.00')
        total_tax = Decimal('0.00')
        total_items_amount = Decimal('0.00')

        # Loop through all purchase items
        for item in obj.purchase_items.all():
            # Item level calculations
            base_amount = Decimal(str(item.quantity)) * item.purchase_price
            item_discount = item.discount_amount
            taxable_amount = base_amount - item_discount
            item_tax = item.tax_amount
            item_total = item.total_amount

            # Accumulate totals
            total_base_amount += base_amount
            total_discount += item_discount
            total_tax += item_tax
            total_items_amount += item_total

            # Build item breakdown
            items_breakdown.append({
                'medication_name': item.medication.name,
                'batch_number': item.batch_number,
                'quantity': item.quantity,
                'purchase_price': str(item.purchase_price),
                'base_amount': str(base_amount),
                'discount_percent': str(item.discount_percent),
                'discount_amount': str(item_discount),
                'taxable_amount': str(taxable_amount),
                'gst_percent': str(item.cgst_percent + item.sgst_percent + item.igst_percent),
                'tax_amount': str(item_tax),
                'item_total': str(item_total),
                'calculation_steps': {
                    'step_1': f"{item.quantity} × {item.purchase_price} = {base_amount}",
                    'step_2': f"{base_amount} - {item_discount} (discount) = {taxable_amount}",
                    'step_3': f"{taxable_amount} × {item.cgst_percent + item.sgst_percent + item.igst_percent}% (GST) = {item_tax}",
                    'step_4': f"{taxable_amount} + {item_tax} = {item_total}"
                }
            })

        # GRN level calculation
        grn_discount = obj.discount_amount
        final_total = obj.total_amount

        return {
            'items_breakdown': items_breakdown,
            'items_summary': {
                'total_base_amount': str(total_base_amount),
                'total_item_discount': str(total_discount),
                'total_taxable_amount': str(total_base_amount - total_discount),
                'total_tax_amount': str(total_tax),
                'total_items_amount': str(total_items_amount)
            },
            'grn_level': {
                'subtotal': str(obj.subtotal),
                'grn_discount': str(grn_discount),
                'tax_amount': str(obj.tax_amount),
                'final_total': str(final_total),
                'calculation_formula': f"Subtotal ({obj.subtotal}) + Tax ({obj.tax_amount}) - GRN Discount ({grn_discount}) = {final_total}"
            },
            'grand_total': str(final_total)
        }

    def validate_supplier(self, value):
        """Validate supplier is active"""
        if not value.is_active:
            raise serializers.ValidationError("Supplier is not active")
        return value

    def validate_items(self, value):
        """Validate items list"""
        if not value or len(value) == 0:
            raise serializers.ValidationError("At least one item is required")
        return value

    @transaction.atomic
    def create(self, validated_data):
        """
        Create GRN with items and create UNVERIFIED stock entries
        Stock will be marked as verified only after pharmacist approval
        """
        items_data = validated_data.pop('items')

        # Create GRN with PENDING status (grn_number auto-generated in model)
        grn = PurchaseEntry.objects.create(**validated_data)

        # Create items and stock entries (UNVERIFIED)
        for item_data in items_data:
            # Create purchase item (calculations done in model save)
            purchase_item = PurchaseItem.objects.create(
                purchase_entry=grn,
                **item_data
            )

            # Auto-create MedicationStock entry (is_verified=False by default)
            total_qty = item_data['quantity'] + item_data.get('free_quantity', 0)

            stock_entry = MedicationStock.objects.create(
                medication=item_data['medication'],
                batch_number=item_data['batch_number'],
                expiry_date=item_data['expiry_date'],
                quantity=total_qty,
                received_quantity=total_qty,
                received_date=grn.received_date,
                purchase_price=item_data['purchase_price'],
                selling_price=item_data.get('mrp', item_data['purchase_price']),  # Default selling = MRP
                mrp=item_data.get('mrp'),
                ptr=item_data.get('ptr'),
                supplier=grn.supplier.name,
                manufacturer=grn.supplier.name,  # Can be updated later
                purchase_entry=grn,
                purchase_item=purchase_item,
                free_quantity=item_data.get('free_quantity', 0),
                # NEW: Copy packing fields from purchase item
                pack_quantity=item_data.get('pack_quantity'),
                units_per_pack=item_data.get('units_per_pack'),
                price_per_pack=item_data.get('price_per_pack'),
                packing=item_data.get('packing'),
                cgst_percent=item_data.get('cgst_percent', 0),
                sgst_percent=item_data.get('sgst_percent', 0),
                igst_percent=item_data.get('igst_percent', 0),
                margin_percent=purchase_item.margin_percent,
                is_verified=False,  # Mark as unverified - pharmacist must approve
                created_by=validated_data.get('created_by')
            )

            # Link stock entry to purchase item
            purchase_item.stock_entry = stock_entry
            purchase_item.save()

        # Calculate and update GRN totals
        grn.calculate_totals()

        return grn


class PurchaseEntryListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing GRNs
    """
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True, allow_null=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    items_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PurchaseEntry
        fields = [
            'id', 'grn_number', 'supplier_name', 'po_number',
            'invoice_number', 'invoice_date', 'received_date',
            'total_amount', 'payment_status', 'payment_status_display',
            'status', 'items_count'
        ]

    def get_items_count(self, obj):
        """Count items"""
        return obj.purchase_items.count()


# ============================================================================
# SUPPLIER RETURN (PURCHASE RETURN) SERIALIZERS
# ============================================================================

class SupplierReturnItemSerializer(serializers.ModelSerializer):
    """
    Serializer for Supplier Return Items (read operations)
    """
    medication_name = serializers.CharField(source='medication.name', read_only=True)
    medication_strength = serializers.CharField(source='medication.strength', read_only=True)
    medication_dosage_form = serializers.CharField(source='medication.dosage_form', read_only=True)
    condition_display = serializers.CharField(source='get_condition_display', read_only=True)

    class Meta:
        model = SupplierReturnItem
        fields = [
            'id', 'medication', 'medication_name', 'medication_strength',
            'medication_dosage_form', 'stock_entry', 'purchase_item',
            'batch_number', 'expiry_date', 'quantity_returned',
            'unit_price', 'cgst_percent', 'sgst_percent', 'igst_percent',
            'tax_amount', 'total_amount', 'condition', 'condition_display',
            'reason_detail'
        ]
        read_only_fields = ['tax_amount', 'total_amount']


class SupplierReturnItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating Supplier Return Items
    """
    class Meta:
        model = SupplierReturnItem
        fields = [
            'medication', 'stock_entry', 'purchase_item',
            'batch_number', 'expiry_date', 'quantity_returned',
            'unit_price', 'cgst_percent', 'sgst_percent', 'igst_percent',
            'condition', 'reason_detail'
        ]

    def validate_quantity_returned(self, value):
        """Validate quantity is positive"""
        if value <= 0:
            raise serializers.ValidationError("Quantity returned must be greater than zero")
        return value

    def validate(self, data):
        """
        Validate supplier return item data

        Note: We don't validate against current available stock because:
        - Returns can be for items already sold/dispensed
        - We're returning based on original receipt, not current stock
        - Stock adjustment happens separately based on condition
        """
        quantity_returned = data.get('quantity_returned', 0)

        # Just validate quantity is positive
        if quantity_returned <= 0:
            raise serializers.ValidationError({
                'quantity_returned': 'Quantity returned must be greater than zero'
            })

        return data


class SupplierReturnSerializer(serializers.ModelSerializer):
    """
    Full serializer for Supplier Returns (read operations)
    """
    return_items = SupplierReturnItemSerializer(many=True, read_only=True)

    # Display fields
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    supplier_code = serializers.CharField(source='supplier.code', read_only=True)
    grn_number = serializers.CharField(source='purchase_entry.grn_number', read_only=True, allow_null=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    # Audit fields
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True, allow_null=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True, allow_null=True)

    # Computed fields
    items_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SupplierReturn
        fields = [
            'id', 'return_number', 'supplier', 'supplier_name', 'supplier_code',
            'purchase_entry', 'grn_number', 'return_date',
            'reason', 'reason_display', 'status', 'status_display',
            'credit_note_number', 'credit_note_date', 'credit_note_amount',
            'subtotal', 'tax_amount', 'total_amount', 'notes',
            'approved_by', 'approved_by_name', 'approved_date',
            'shipped_date', 'completed_date', 'stock_adjusted',
            'return_items', 'items_count',
            'created_by_name', 'created_on', 'updated_by_name', 'updated_on',
            'is_active'
        ]
        read_only_fields = [
            'return_number', 'subtotal', 'tax_amount', 'total_amount',
            'stock_adjusted', 'created_on', 'updated_on'
        ]

    def get_items_count(self, obj):
        """Count return items"""
        return obj.return_items.count()


class SupplierReturnCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating Supplier Returns with nested items
    """
    items = SupplierReturnItemCreateSerializer(many=True, write_only=True)
    return_items = SupplierReturnItemSerializer(many=True, read_only=True)

    class Meta:
        model = SupplierReturn
        fields = [
            'supplier', 'purchase_entry', 'return_date', 'reason', 'status',
            'notes', 'items', 'return_items'
        ]

    def validate_supplier(self, value):
        """Validate supplier is active"""
        if not value.is_active:
            raise serializers.ValidationError("Supplier is not active")
        return value

    def validate_return_date(self, value):
        """Validate return date is not in future"""
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError("Return date cannot be in the future")
        return value

    def validate_items(self, value):
        """Validate at least one item is being returned"""
        if not value or len(value) == 0:
            raise serializers.ValidationError("At least one item must be returned")
        return value

    def validate(self, data):
        """
        Cross-field validation
        """
        # If GRN is specified, ensure supplier matches
        purchase_entry = data.get('purchase_entry')
        supplier = data.get('supplier')

        if purchase_entry and supplier:
            if purchase_entry.supplier != supplier:
                raise serializers.ValidationError({
                    'supplier': 'Supplier must match the supplier from the selected GRN'
                })

        return data

    @transaction.atomic
    def create(self, validated_data):
        """
        Create supplier return with nested items
        Auto-adjust stock when return is created
        """
        items_data = validated_data.pop('items')

        # Create the return header
        supplier_return = SupplierReturn.objects.create(**validated_data)

        # Create return items
        for item_data in items_data:
            # If stock_entry provided, auto-populate batch and expiry
            stock_entry = item_data.get('stock_entry')
            if stock_entry:
                if not item_data.get('batch_number'):
                    item_data['batch_number'] = stock_entry.batch_number
                if not item_data.get('expiry_date'):
                    item_data['expiry_date'] = stock_entry.expiry_date

                # Auto-populate GST from stock if not provided
                if not item_data.get('cgst_percent') and hasattr(stock_entry, 'cgst_percent'):
                    item_data['cgst_percent'] = stock_entry.cgst_percent or 0
                if not item_data.get('sgst_percent') and hasattr(stock_entry, 'sgst_percent'):
                    item_data['sgst_percent'] = stock_entry.sgst_percent or 0
                if not item_data.get('igst_percent') and hasattr(stock_entry, 'igst_percent'):
                    item_data['igst_percent'] = stock_entry.igst_percent or 0

            SupplierReturnItem.objects.create(
                supplier_return=supplier_return,
                **item_data
            )

        # Calculate totals from items
        supplier_return.calculate_totals()

        # Note: Stock adjustment happens when return is APPROVED, not on creation
        # This allows for cancellation before stock is affected

        return supplier_return


class SupplierReturnListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing supplier returns
    """
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    grn_number = serializers.CharField(source='purchase_entry.grn_number', read_only=True, allow_null=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SupplierReturn
        fields = [
            'id', 'return_number', 'supplier_name', 'grn_number',
            'return_date', 'reason', 'reason_display',
            'status', 'status_display', 'total_amount', 'items_count',
            'credit_note_number', 'credit_note_amount'
        ]

    def get_items_count(self, obj):
        """Count return items"""
        return obj.return_items.count()


# ============================================================================
# MEDICATION SERIALIZERS
# ============================================================================

class MedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medication
        exclude = ['created_on', 'updated_on', 'created_by', 'updated_by','description']
        # fields = '__all__'

    def validate(self, data):
        """
        Check for duplicate medications based on name, dosage_form, and strength.
        A medication is considered duplicate if it has the same combination of these fields.
        """
        name = data.get('name', '').strip()
        dosage_form = data.get('dosage_form', '').strip()
        strength = data.get('strength', '').strip()

        # Normalize the inputs for case-insensitive comparison
        if name:
            data['name'] = name
        if dosage_form:
            data['dosage_form'] = dosage_form
        if strength:
            data['strength'] = strength

        # Check if medication with same name, dosage_form, and strength already exists
        # Exclude the current instance during update operations
        query = Medication.objects.filter(
            name__iexact=name,
            dosage_form__iexact=dosage_form,
            strength__iexact=strength,
            is_active=True
        )

        # If updating, exclude the current instance
        if self.instance:
            query = query.exclude(pk=self.instance.pk)

        if query.exists():
            raise serializers.ValidationError({
                "detail": f"A medication with name '{name}', dosage form '{dosage_form}', and strength '{strength}' already exists in the catalog."
            })

        return data

class MedicationStockSerializer(serializers.ModelSerializer):
    expiration_status = serializers.CharField(source='get_expiration_status', read_only=True)
    days_to_expiry = serializers.SerializerMethodField(read_only=True)
    current_stock = serializers.IntegerField(source='get_current_stock', read_only=True)

    # Audit fields - read only, displayed for audit trail
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True, allow_null=True)

    def get_days_to_expiry(self, obj):
        """Calculate days to expiry"""
        return obj.days_to_expiry()

    class Meta:
        model = MedicationStock
        # Exclude audit fields from input, but we'll handle them in the view
        exclude = ['created_by', 'updated_by']
        # fields = '__all__'
        extra_kwargs = {
            'medication': {'required': True},
            'batch_number': {'required': True},
            'opening_quantity': {'required': False, 'default': 0},
            'received_quantity': {'required': False, 'default': 0},
            'sold_quantity': {'required': False, 'default': 0},
            'returned_quantity': {'required': False, 'default': 0},
            'damaged_quantity': {'required': False, 'default': 0},
            'adjusted_quantity': {'required': False, 'default': 0},
            'is_active': {'required': False, 'default': True},
            # Audit fields - read only
            'created_on': {'read_only': True},
            'updated_on': {'read_only': True},
        }

    def validate(self, data):
        """Validate quantity fields"""
        # Ensure quantity fields are non-negative (except adjusted_quantity which can be negative)
        for field in ['opening_quantity', 'received_quantity', 'sold_quantity',
                      'returned_quantity', 'damaged_quantity']:
            if field in data and data[field] < 0:
                raise serializers.ValidationError(f"{field} cannot be negative")
        return data


class DispenseSerializer(serializers.Serializer):
    medication_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(min_value=1, required=True)



class PharmacistSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacistStaff
        fields = '__all__'
        
        

class Bill_Serializer(serializers.ModelSerializer):
    class Meta:
        model = PatientBill
        fields = '__all__'



#===============================================Labortary Bill ==========================================#

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabDepartment
        fields = ['name', 'code', 'description', 'rate']
        
    def validate_name(self, value):
        """Validate department name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Department name cannot be empty")
        return value.strip()
    
    def validate_code(self, value):
        """Validate department code"""
        if not value or not value.strip():
            raise serializers.ValidationError("Department code cannot be empty")
        if len(value.strip()) > 10:
            raise serializers.ValidationError("Department code cannot exceed 10 characters")
        return value.strip().upper()
    
    def validate_rate(self, value):
        """Validate rate if provided"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Rate cannot be negative")
        return value
    
    
    
class TestCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCategory
        fields = ['department', 'name', 'code', 'description', 'parent']
        
    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Category name cannot be empty")
        return value.strip()
    
    def validate_code(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Category code cannot be empty")
        if len(value.strip()) > 20:
            raise serializers.ValidationError("Category code cannot exceed 20 characters")
        return value.strip().upper()
    
    def validate_department(self, value):
        if not value:
            raise serializers.ValidationError("Department is required")
        return value
    
    def validate_parent(self, value):
        if value and value.parent:
            raise serializers.ValidationError("Cannot create subcategory under another subcategory")
        return value

class TestParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestParameter
        fields = ['category', 'name', 'code', 'unit', 'is_qualitative', 'normal_values', 'sequence_order', 'is_active']
        
    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Parameter name cannot be empty")
        return value.strip()
    
    def validate_code(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Parameter code cannot be empty")
        if len(value.strip()) > 20:
            raise serializers.ValidationError("Parameter code cannot exceed 20 characters")
        return value.strip().upper()
    
    def validate_category(self, value):
        if not value:
            raise serializers.ValidationError("Category is required")
        return value
    
    def validate_sequence_order(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Sequence order must be at least 1")
        return value or 1


class ReferenceRangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferenceRange
        fields = ['parameter', 'gender', 'age_min', 'age_max', 'min_val', 'max_val', 'note']
        
    def validate_parameter(self, value):
        if not value:
            raise serializers.ValidationError("Parameter is required")
        return value
    
    def validate_min_val(self, value):
        if value is None:
            raise serializers.ValidationError("Minimum value is required")
        return value
    
    def validate_max_val(self, value):
        if value is None:
            raise serializers.ValidationError("Maximum value is required")
        return value
    
    def validate(self, data):
        if data['min_val'] >= data['max_val']:
            raise serializers.ValidationError("Minimum value must be less than maximum value")
        
        if data.get('age_min') and data.get('age_max'):
            if data['age_min'] >= data['age_max']:
                raise serializers.ValidationError("Minimum age must be less than maximum age")
        
        return data
        

class LabReferenceRangeSerializer(serializers.ModelSerializer):
    age_range_display = serializers.SerializerMethodField()
    range_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ReferenceRange
        fields = ['id', 'gender', 'age_min', 'age_max', 'min_val', 'max_val', 'note', 'age_range_display', 'range_display']
    
    def get_age_range_display(self, obj):
        return f"{obj.age_min or 0}-{obj.age_max or '∞'} years"
    
    def get_range_display(self, obj):
        return f"{obj.min_val} - {obj.max_val} {obj.parameter.unit}"

class LabTestParameterSerializer(serializers.ModelSerializer):
    reference_ranges = LabReferenceRangeSerializer(many=True, read_only=True)
    
    class Meta:
        model = TestParameter
        fields = ['id', 'name', 'code', 'unit', 'is_qualitative', 'normal_values', 'sequence_order', 'reference_ranges']

class LabTestCategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()
    parameters = LabTestParameterSerializer(many=True, read_only=True)
    
    class Meta:
        model = TestCategory
        fields = ['id', 'name', 'code', 'description', 'subcategories', 'parameters']
    
    def get_subcategories(self, obj):
        subcategories = obj.subcategories.all()
        return TestCategorySerializer(subcategories, many=True).data

class LabDepartmentSerializer(serializers.ModelSerializer):
    categories = serializers.SerializerMethodField()

    class Meta:
        model = LabDepartment
        fields = ['id', 'name', 'code', 'description', 'rate', 'categories']

    def get_categories(self, obj):
        # Only get main categories (without parent)
        main_categories = obj.categories.filter(parent__isnull=True)
        return LabTestCategorySerializer(main_categories, many=True).data


class LabDepartmentSimpleSerializer(serializers.ModelSerializer):
    """
    Lightweight Lab Department Serializer for Order Creation

    Purpose:
        Returns only essential fields needed for lab order creation.
        No nested data, minimal payload.

    Fields:
        - id: Department ID (required for order creation)
        - name: Department/Test name (for display)
        - rate: Price (for total calculation)

    Use Case:
        - Lab test selection dropdown
        - Order creation form
        - Quick test lookup

    Example Response:
        {
            "id": 1,
            "name": "Hematology (CBC)",
            "rate": 500
        }
    """
    class Meta:
        model = LabDepartment
        fields = ['id', 'name', 'rate']
        read_only_fields = ['id', 'name', 'rate']



#=============================================== MEDICINE RETURNS ==========================================#

class MedicineReturnItemSerializer(serializers.ModelSerializer):
    """
    Serializer for individual medicine return items
    """
    medication_name = serializers.CharField(source='medication.name', read_only=True)
    medication_strength = serializers.CharField(source='medication.strength', read_only=True)
    medication_dosage_form = serializers.CharField(source='medication.dosage_form', read_only=True)
    batch_number_display = serializers.CharField(source='batch_number', read_only=True)
    condition_display = serializers.CharField(source='get_condition_display', read_only=True)

    class Meta:
        model = PatientMedicineReturnItem
        fields = [
            'id',
            'medication',
            'medication_name',
            'medication_strength',
            'medication_dosage_form',
            'stock_entry',
            'batch_number',
            'batch_number_display',
            'expiry_date',
            'quantity_returned',
            'unit_price',
            'refund_amount',
            'condition',
            'condition_display',
            'can_restock'
        ]
        read_only_fields = ['refund_amount', 'can_restock']


class MedicineReturnCreateItemSerializer(serializers.ModelSerializer):
    """
    Serializer for creating medicine return items
    """
    class Meta:
        model = PatientMedicineReturnItem
        fields = [
            'medication',
            'stock_entry',
            'quantity_returned',
            'unit_price',
            'condition'
        ]

    def validate_quantity_returned(self, value):
        """Validate quantity is positive"""
        if value <= 0:
            raise serializers.ValidationError("Quantity returned must be greater than zero")
        return value

    def validate(self, data):
        """
        Validate that medication matches stock entry
        """
        if data.get('medication') and data.get('stock_entry'):
            if data['stock_entry'].medication != data['medication']:
                raise serializers.ValidationError({
                    'medication': 'Medication must match the stock entry medication'
                })
        return data


class MedicineReturnSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for medicine returns (read operations)
    Supports both PatientBill and PharmacyBilling
    """
    items = MedicineReturnItemSerializer(many=True, read_only=True)

    # Patient details
    patient_name = serializers.SerializerMethodField()
    patient_mobile = serializers.SerializerMethodField()

    # Bill details - works for both bill types
    bill_number = serializers.SerializerMethodField()
    bill_date = serializers.SerializerMethodField()
    bill_type = serializers.SerializerMethodField()

    # Processing details
    processed_by_name = serializers.SerializerMethodField()
    refund_method_display = serializers.CharField(source='get_refund_method_display', read_only=True)

    # Computed fields
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = PatientMedicineReturn
        fields = [
            'id',
            'return_number',
            'patient',
            'patient_name',
            'patient_mobile',
            'patient_bill',
            'pharmacy_bill',
            'bill_type',
            'bill_number',
            'bill_date',
            'return_date',
            'total_refund_amount',
            'refund_method',
            'refund_method_display',
            'is_refunded',
            'processed_by',
            'processed_by_name',
            'processed_date',
            'stock_adjusted',
            'notes',
            'items',
            'items_count',
            'created_on',
            'updated_on'
        ]
        read_only_fields = [
            'return_number',
            'total_refund_amount',
            'is_refunded',
            'stock_adjusted',
            'created_on',
            'updated_on'
        ]

    def get_patient_name(self, obj):
        if obj.patient:
            return f"{obj.patient.first_name} {obj.patient.last_name}"
        elif obj.pharmacy_bill:
            return obj.pharmacy_bill.patient_name
        return "N/A"

    def get_patient_mobile(self, obj):
        if obj.patient:
            return obj.patient.contact_number
        return None

    def get_bill_number(self, obj):
        if obj.patient_bill:
            return obj.patient_bill.bill_number
        elif obj.pharmacy_bill:
            return obj.pharmacy_bill.bill_number
        return None

    def get_bill_date(self, obj):
        if obj.patient_bill:
            return obj.patient_bill.bill_date
        elif obj.pharmacy_bill:
            return obj.pharmacy_bill.bill_date
        return None

    def get_bill_type(self, obj):
        if obj.patient_bill:
            return "PATIENT_BILL"
        elif obj.pharmacy_bill:
            return "PHARMACY_BILL"
        return None

    def get_processed_by_name(self, obj):
        if obj.processed_by:
            return obj.processed_by.get_full_name() or obj.processed_by.username
        return None

    def get_items_count(self, obj):
        return obj.items.count()


class MedicineReturnCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating medicine returns
    Supports both PatientBill (consultation-based) and PharmacyBilling (OTC sales)
    """
    items = MedicineReturnCreateItemSerializer(many=True, write_only=True)

    class Meta:
        model = PatientMedicineReturn
        fields = [
            'patient',
            'patient_bill',
            'pharmacy_bill',
            'refund_method',
            'notes',
            'items'
        ]

    def validate_patient_bill(self, value):
        """Validate patient bill exists and is paid"""
        if value and value.payment_status != 'PAID':
            raise serializers.ValidationError("Can only return medicines from paid bills")
        return value

    def validate_pharmacy_bill(self, value):
        """Validate pharmacy bill exists and is paid"""
        if value and value.payment_status != 'PAID':
            raise serializers.ValidationError("Can only return medicines from paid bills")
        return value

    def validate_items(self, value):
        """Validate at least one item is being returned"""
        if not value or len(value) == 0:
            raise serializers.ValidationError("At least one item must be returned")
        return value

    def validate(self, data):
        """
        Validate:
        1. Exactly one bill type is provided
        2. Patient matches bill patient (if applicable)
        """
        patient_bill = data.get('patient_bill')
        pharmacy_bill = data.get('pharmacy_bill')

        # Check that exactly one bill type is provided
        if not patient_bill and not pharmacy_bill:
            raise serializers.ValidationError(
                "Either patient_bill or pharmacy_bill must be provided"
            )

        if patient_bill and pharmacy_bill:
            raise serializers.ValidationError(
                "Cannot provide both patient_bill and pharmacy_bill"
            )

        # Validate patient matches bill patient (for PatientBill)
        if patient_bill and data.get('patient'):
            bill_patient = patient_bill.appointment.patient
            if data['patient'] != bill_patient:
                raise serializers.ValidationError({
                    'patient': 'Patient must match the patient from the bill'
                })

        # For PharmacyBilling, patient is optional (OTC sales may not have registered patient)
        # No additional validation needed

        return data

    def create(self, validated_data):
        """
        Create medicine return with items
        """
        from django.db import transaction
        from django.utils import timezone

        items_data = validated_data.pop('items')

        with transaction.atomic():
            # Create the return record
            medicine_return = PatientMedicineReturn.objects.create(**validated_data)

            # Create return items
            for item_data in items_data:
                PatientMedicineReturnItem.objects.create(
                    patient_return=medicine_return,
                    **item_data
                )

            # Calculate total refund amount
            medicine_return.total_refund_amount = sum(
                item.refund_amount for item in medicine_return.items.all()
            )
            medicine_return.save(update_fields=['total_refund_amount'])

        return medicine_return


class MedicineReturnProcessSerializer(serializers.Serializer):
    """
    Serializer for processing refund
    """
    refund_method = serializers.ChoiceField(
        choices=[
            ('CASH', 'Cash'),
            ('CARD', 'Card'),
            ('UPI', 'UPI'),
            ('ORIGINAL_MODE', 'Original Payment Mode')
        ],
        required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """Validate return can be processed"""
        medicine_return = self.context.get('medicine_return')

        if not medicine_return:
            raise serializers.ValidationError("Medicine return not found in context")

        if medicine_return.is_refunded:
            raise serializers.ValidationError("This return has already been refunded")

        if medicine_return.items.count() == 0:
            raise serializers.ValidationError("Cannot process return with no items")

        return data


# ============================================================================
# LAB TEST ORDER SERIALIZERS (External Lab Management)
# ============================================================================

class LabPaymentTransactionSerializer(serializers.ModelSerializer):
    """
    Lab Payment Transaction Serializer

    Purpose:
        Serializes individual payment transactions for lab orders.
        Tracks partial payments with full audit trail.

    Features:
        - Auto-generates transaction ID
        - Displays payment type label
        - Shows staff who received payment
        - Read-only transaction date
        - Supports multiple payment methods

    Usage:
        Used in nested serialization within LabTestOrderSerializer
        and for recording new payments.
    """
    # Display fields
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    received_by_name = serializers.CharField(source='received_by.username', read_only=True)

    class Meta:
        model = LabPaymentTransaction
        fields = [
            'id', 'transaction_id', 'amount',
            'payment_type', 'payment_type_display',
            'payment_date', 'received_by', 'received_by_name',
            'receipt_number', 'notes',
            'created_on'
        ]
        read_only_fields = ['transaction_id', 'payment_date', 'created_on']


class LabTestResultSerializer(serializers.ModelSerializer):
    """
    Lab Test Result Serializer

    Purpose:
        Handles PDF upload and metadata for lab reports.
        Manages file storage and retrieval.

    Features:
        - File upload validation (PDF only)
        - Auto-extract file metadata
        - Display uploader name
        - File size formatting
        - Read-only upload timestamp

    Validation:
        - Only PDF files allowed
        - File size limit (configurable)
        - Required fields check
    """
    # Display fields
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    patient_name = serializers.CharField(source='patient.first_name', read_only=True)
    report_pdf_url = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()

    class Meta:
        model = LabTestResult
        fields = [
            'id', 'lab_order', 'patient', 'patient_name',
            'report_pdf', 'report_pdf_url', 'report_date',
            'uploaded_by', 'uploaded_by_name', 'uploaded_on',
            'file_name', 'file_size', 'file_size_display',
            'notes', 'created_on'
        ]
        read_only_fields = ['uploaded_on', 'file_size', 'file_name', 'created_on']

    def get_report_pdf_url(self, obj):
        """Get full URL for PDF file"""
        if obj.report_pdf:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.report_pdf.url)
            return obj.report_pdf.url
        return None

    def get_file_size_display(self, obj):
        """Format file size in human-readable format"""
        if not obj.file_size:
            return "0 KB"

        size = obj.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"

    def validate_report_pdf(self, value):
        """Validate PDF file"""
        if value:
            # Check file extension
            if not value.name.lower().endswith('.pdf'):
                raise serializers.ValidationError("Only PDF files are allowed")

            # Check file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if value.size > max_size:
                raise serializers.ValidationError(
                    f"File size cannot exceed 10MB. Current size: {value.size / (1024 * 1024):.2f}MB"
                )

        return value

    def create(self, validated_data):
        """
        Auto-populate file_name and file_size from uploaded PDF
        """
        report_pdf = validated_data.get('report_pdf')

        if report_pdf:
            # Auto-extract filename from uploaded file
            if 'file_name' not in validated_data:
                validated_data['file_name'] = report_pdf.name

            # Auto-extract file size
            if 'file_size' not in validated_data:
                validated_data['file_size'] = report_pdf.size

        return super().create(validated_data)


class LabTestOrderSerializer(serializers.ModelSerializer):
    """
    Lab Test Order Serializer

    Purpose:
        Main serializer for lab test orders sent to external labs.
        Handles order creation, payment tracking, and status management.

    Features:
        - Auto-generates order number
        - Nested payment transactions
        - Nested test results
        - Status display labels
        - Patient details
        - Payment summary calculations
        - Supports walk-in and appointment-based orders

    Fields:
        patient: Patient ID (required)
        appointment: Appointment ID (optional - null for walk-ins)
        selected_tests: JSON array of test details
        external_lab_name: External lab name
        status: Order status
        payment_status: Payment status
        total_amount, paid_amount, balance_amount: Payment tracking
        payments: Nested payment transactions (read-only)
        results: Nested test results (read-only)

    Validation:
        - Validates patient exists
        - Validates appointment belongs to patient
        - Validates payment amounts
        - Validates selected_tests format

    Example:
        {
            "patient": 1,
            "appointment": null,  # Walk-in
            "selected_tests": [
                {"id": 1, "name": "CBC", "category": "Hematology", "price": 500}
            ],
            "total_amount": 500,
            "paid_amount": 200,
            "discount": 0,
            "external_lab_name": "Path Lab",
            "status": "ORDERED"
        }
    """
    # Display fields
    patient_name = serializers.SerializerMethodField()
    patient_phone = serializers.CharField(source='patient.contact_number', read_only=True)
    patient_id_display = serializers.CharField(source='patient.patient_id', read_only=True)
    patient_age = serializers.IntegerField(source='patient.age', read_only=True)
    patient_gender = serializers.CharField(source='patient.get_gender_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)

    # Nested serializers
    payments = LabPaymentTransactionSerializer(many=True, read_only=True)
    results = LabTestResultSerializer(many=True, read_only=True)

    # Audit fields
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = LabTestOrder
        fields = [
            'id', 'order_number', 'patient', 'patient_name', 'patient_phone', 'patient_id_display',
            'patient_age', 'patient_gender',
            'appointment', 'lab_departments', 'selected_tests',
            'external_lab_name', 'external_reference_number',
            'status', 'status_display',
            'total_amount', 'paid_amount', 'balance_amount', 'discount',
            'payment_status', 'payment_status_display',
            'date_ordered', 'date_sent', 'date_received',
            'special_instructions',
            'payments', 'results',
            'created_by', 'created_by_name', 'created_on',
            'updated_by', 'updated_on', 'is_active'
        ]
        read_only_fields = [
            'order_number', 'balance_amount', 'date_ordered',
            'created_on', 'updated_on', 'payments', 'results'
        ]

    def get_patient_name(self, obj):
        """Get patient full name"""
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    def validate(self, data):
        """Validate lab test order data"""
        # Validate appointment belongs to patient
        if data.get('appointment') and data.get('patient'):
            if data['appointment'].patient != data['patient']:
                raise serializers.ValidationError({
                    'appointment': 'Appointment does not belong to the selected patient'
                })

        # Validate selected_tests format
        selected_tests = data.get('selected_tests', [])
        if not isinstance(selected_tests, list):
            raise serializers.ValidationError({
                'selected_tests': 'Must be a list of test objects'
            })

        if not selected_tests:
            raise serializers.ValidationError({
                'selected_tests': 'At least one test must be selected'
            })

        # Validate each test has required fields
        for test in selected_tests:
            if not isinstance(test, dict):
                raise serializers.ValidationError({
                    'selected_tests': 'Each test must be an object'
                })

            required_fields = ['id', 'name', 'price']
            for field in required_fields:
                if field not in test:
                    raise serializers.ValidationError({
                        'selected_tests': f'Each test must have: {", ".join(required_fields)}'
                    })

        # Validate payment amounts
        total = data.get('total_amount', 0)
        paid = data.get('paid_amount', 0)
        discount = data.get('discount', 0)

        if paid < 0:
            raise serializers.ValidationError({
                'paid_amount': 'Paid amount cannot be negative'
            })

        if discount < 0:
            raise serializers.ValidationError({
                'discount': 'Discount cannot be negative'
            })

        if paid > total:
            raise serializers.ValidationError({
                'paid_amount': 'Paid amount cannot exceed total amount'
            })

        if discount > total:
            raise serializers.ValidationError({
                'discount': 'Discount cannot exceed total amount'
            })

        # Auto-set payment status based on amounts
        balance = total - paid - discount
        if balance <= 0:
            data['payment_status'] = 'PAID'
        elif paid == 0:
            data['payment_status'] = 'UNPAID'
        else:
            data['payment_status'] = 'PARTIALLY_PAID'

        return data

    def create(self, validated_data):
        """Create lab test order with audit fields"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user

        return super().create(validated_data)


class LabTestOrderListSerializer(serializers.ModelSerializer):
    """
    Lab Test Order List Serializer (Lightweight)

    Purpose:
        Lightweight serializer for list views.
        Excludes nested objects for better performance.

    Usage:
        Use this for GET list endpoints
        Use LabTestOrderSerializer for detail view
    """
    patient_name = serializers.SerializerMethodField()
    patient_phone = serializers.CharField(source='patient.contact_number', read_only=True)
    patient_age = serializers.IntegerField(source='patient.age', read_only=True)
    patient_gender = serializers.CharField(source='patient.get_gender_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    test_count = serializers.SerializerMethodField()
    has_results = serializers.SerializerMethodField()

    class Meta:
        model = LabTestOrder
        fields = [
            'id', 'order_number', 'patient', 'patient_name', 'patient_phone',
            'patient_age', 'patient_gender',
            'lab_departments',
            'status', 'status_display',
            'payment_status', 'payment_status_display',
            'total_amount', 'paid_amount', 'balance_amount',
            'test_count', 'has_results',
            'date_ordered', 'date_sent', 'date_received',
            'external_lab_name'
        ]

    def get_patient_name(self, obj):
        """Get patient full name"""
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    def get_test_count(self, obj):
        """Count selected tests"""
        return len(obj.selected_tests) if obj.selected_tests else 0

    def get_has_results(self, obj):
        """Check if results uploaded"""
        return obj.results.exists()


# ============================================================================
# STOCK ALLOCATION & TRANSFER SERIALIZERS
# ============================================================================

class StockAllocationSerializer(serializers.Serializer):
    """
    Serializer for allocating stock to departments
    """
    stock_entry = serializers.IntegerField(help_text="MedicationStock ID")
    pharmacy_quantity = serializers.IntegerField(min_value=0, required=False, default=0)
    home_care_quantity = serializers.IntegerField(min_value=0, required=False, default=0)
    casualty_quantity = serializers.IntegerField(min_value=0, required=False, default=0)

    def validate(self, data):
        """Validate allocation doesn't exceed available stock"""
        from apps.data_hub.models import MedicationStock

        try:
            stock = MedicationStock.objects.get(id=data['stock_entry'])
        except MedicationStock.DoesNotExist:
            raise serializers.ValidationError("Stock entry not found")

        # Calculate total allocation requested
        total_allocation = (
            data.get('pharmacy_quantity', 0) +
            data.get('home_care_quantity', 0) +
            data.get('casualty_quantity', 0)
        )

        # Check against available quantity
        if total_allocation > stock.quantity:
            raise serializers.ValidationError({
                'non_field_errors': [
                    f"Total allocation ({total_allocation}) exceeds available stock ({stock.quantity})"
                ]
            })

        data['stock'] = stock
        return data


class StockTransferCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating stock transfers
    """
    class Meta:
        model = StockTransfer
        fields = [
            'stock_entry',
            'from_department',
            'to_department',
            'quantity_transferred',
            'reason'
        ]

    def validate(self, data):
        """Validate transfer"""
        # Cannot transfer to same department
        if data['from_department'] == data['to_department']:
            raise serializers.ValidationError({
                'to_department': 'Cannot transfer to the same department'
            })

        # Check if source department has enough quantity
        stock = data['stock_entry']
        qty = data['quantity_transferred']

        if data['from_department'] == 'PHARMACY':
            available = stock.pharmacy_quantity
        elif data['from_department'] == 'HOME_CARE':
            available = stock.home_care_quantity
        elif data['from_department'] == 'CASUALTY':
            available = stock.casualty_quantity
        else:
            available = 0

        if qty > available:
            raise serializers.ValidationError({
                'quantity_transferred': f"Insufficient quantity in {data['from_department']}. Available: {available}"
            })

        return data

    def create(self, validated_data):
        """Create transfer and process it"""
        from django.db import transaction

        with transaction.atomic():
            # Set transferred_by from request user
            validated_data['transferred_by'] = self.context['request'].user

            # Create transfer
            transfer = StockTransfer.objects.create(**validated_data)

            # Process the transfer immediately
            transfer.process_transfer()

        return transfer


class StockTransferSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for stock transfers (read operations)
    """
    medication_name = serializers.CharField(source='stock_entry.medication.name', read_only=True)
    batch_number = serializers.CharField(source='stock_entry.batch_number', read_only=True)
    from_department_display = serializers.CharField(source='get_from_department_display', read_only=True)
    to_department_display = serializers.CharField(source='get_to_department_display', read_only=True)
    transferred_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = StockTransfer
        fields = [
            'id',
            'stock_entry',
            'medication_name',
            'batch_number',
            'from_department',
            'from_department_display',
            'to_department',
            'to_department_display',
            'quantity_transferred',
            'reason',
            'transferred_by',
            'transferred_by_name',
            'transfer_date',
            'status',
            'status_display',
            'created_on',
            'updated_on'
        ]
        read_only_fields = ['transfer_date', 'created_on', 'updated_on']

    def get_transferred_by_name(self, obj):
        if obj.transferred_by:
            return obj.transferred_by.get_full_name() or obj.transferred_by.username
        return None


class MedicationStockAllocationSerializer(serializers.ModelSerializer):
    """
    Serializer for medication stock with allocation details
    """
    medication_name = serializers.CharField(source='medication.name', read_only=True)
    medication_strength = serializers.CharField(source='medication.strength', read_only=True)
    unallocated_quantity = serializers.SerializerMethodField()
    allocated_total = serializers.SerializerMethodField()

    class Meta:
        model = MedicationStock
        fields = [
            'id',
            'medication',
            'medication_name',
            'medication_strength',
            'batch_number',
            'quantity',
            'pharmacy_quantity',
            'home_care_quantity',
            'casualty_quantity',
            'unallocated_quantity',
            'allocated_total',
            'expiry_date',
            'purchase_price',
            'selling_price'
        ]
        read_only_fields = ['unallocated_quantity', 'allocated_total']

    def get_unallocated_quantity(self, obj):
        return obj.get_unallocated_quantity()

    def get_allocated_total(self, obj):
        return obj.get_allocated_total()
