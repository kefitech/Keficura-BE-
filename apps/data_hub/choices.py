"""
Hospital Information System - Centralized Choices/Constants
===========================================================

Author: Athul Gopan
Created: 2025-12-01
Description: Centralized choices and constants for all models in the HIS system.
            This file contains all dropdown options, status choices, and constant
            values used across multiple models to ensure consistency and reusability.

Usage:
    from apps.data_hub.choices import *

    class MyModel(models.Model):
        status = models.CharField(choices=PAYMENT_STATUS_CHOICES)
"""

# ============================================================================
# PAYMENT & BILLING CHOICES
# ============================================================================

PAYMENT_TYPE_CHOICES = [
    ('CASH', 'Cash Only'),
    ('CREDIT', 'Credit Allowed'),
    ('BOTH', 'Cash & Credit'),
]

PAYMENT_MODE_CHOICES = [
    ('CASH', 'Cash'),
    ('CARD', 'Card'),
    ('UPI', 'UPI'),
    ('CHEQUE', 'Cheque'),
    ('NETBANKING', 'Net Banking'),
    ('CREDIT', 'Credit'),
]

PAYMENT_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('PAID', 'Paid'),
    ('PARTIAL', 'Partial'),
    ('OVERDUE', 'Overdue'),
    ('CANCELLED', 'Cancelled'),
]

# ============================================================================
# PHARMACY CHOICES
# ============================================================================

DOSAGE_FORM_CHOICES = [
    ('TABLET', 'Tablet'),
    ('CAPSULE', 'Capsule'),
    ('SYRUP', 'Syrup'),
    ('INJECTION', 'Injection'),
    ('CREAM', 'Cream'),
    ('OINTMENT', 'Ointment'),
    ('DROP', 'Drop'),
    ('INHALER', 'Inhaler'),
    ('POWDER', 'Powder'),
    ('SOLUTION', 'Solution'),
    ('SUSPENSION', 'Suspension'),
    ('GEL', 'Gel'),
    ('LOTION', 'Lotion'),
    ('SPRAY', 'Spray'),
]

MEDICINE_RETURN_CONDITION_CHOICES = [
    ('UNOPENED', 'Unopened'),
    ('OPENED', 'Opened'),
    ('DAMAGED', 'Damaged'),
    ('EXPIRED', 'Expired'),
]

REFUND_METHOD_CHOICES = [
    ('CASH', 'Cash'),
    ('CARD', 'Card'),
    ('UPI', 'UPI'),
    ('ORIGINAL_MODE', 'Original Payment Mode'),
]

EXPIRY_STATUS_CHOICES = [
    ('VALID', 'Valid'),
    ('NEAR_EXPIRY', 'Near Expiry'),
    ('EXPIRED', 'Expired'),
]

# ============================================================================
# PURCHASE & STOCK CHOICES
# ============================================================================

PURCHASE_ORDER_STATUS_CHOICES = [
    ('DRAFT', 'Draft'),
    ('PENDING', 'Pending'),
    ('APPROVED', 'Approved'),
    ('PARTIAL', 'Partially Received'),
    ('COMPLETED', 'Completed'),
    ('CANCELLED', 'Cancelled'),
]

GRN_STATUS_CHOICES = [
    ('PENDING', 'Pending Approval'),
    ('APPROVED', 'Approved'),
    ('REJECTED', 'Rejected'),
]

PURCHASE_RETURN_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('APPROVED', 'Approved'),
    ('SHIPPED', 'Shipped to Supplier'),
    ('COMPLETED', 'Completed'),
    ('REJECTED', 'Rejected'),
    ('CANCELLED', 'Cancelled'),
]

PURCHASE_RETURN_REASON_CHOICES = [
    ('DAMAGED', 'Damaged Goods'),
    ('EXPIRED', 'Expired Items'),
    ('WRONG_ITEM', 'Wrong Item Received'),
    ('EXCESS_STOCK', 'Excess Stock'),
    ('NEAR_EXPIRY', 'Near Expiry'),
    ('QUALITY_ISSUE', 'Quality Issue'),
    ('OTHER', 'Other'),
]

ITEM_CONDITION_CHOICES = [
    ('GOOD', 'Good Condition'),
    ('DAMAGED', 'Damaged'),
    ('EXPIRED', 'Expired'),
    ('NEAR_EXPIRY', 'Near Expiry'),
]

STOCK_ADJUSTMENT_TYPE_CHOICES = [
    ('ADDITION', 'Addition'),
    ('DEDUCTION', 'Deduction'),
    ('DAMAGE', 'Damage'),
    ('EXPIRY', 'Expiry'),
    ('RETURN', 'Return'),
    ('TRANSFER', 'Transfer'),
    ('CORRECTION', 'Correction'),
]

STOCK_TRANSFER_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('IN_TRANSIT', 'In Transit'),
    ('RECEIVED', 'Received'),
    ('REJECTED', 'Rejected'),
    ('CANCELLED', 'Cancelled'),
]

CONSUMPTION_TYPE_CHOICES = [
    ('INTERNAL', 'Internal Use'),
    ('DEPARTMENT', 'Department Consumption'),
    ('EMERGENCY', 'Emergency Use'),
    ('SAMPLE', 'Sample'),
    ('DAMAGE', 'Damage/Wastage'),
]

# ============================================================================
# SUPPLIER & VENDOR CHOICES
# ============================================================================

SUPPLIER_TYPE_CHOICES = [
    ('MANUFACTURER', 'Manufacturer'),
    ('DISTRIBUTOR', 'Distributor'),
    ('WHOLESALER', 'Wholesaler'),
    ('RETAILER', 'Retailer'),
    ('AGENT', 'Agent'),
]

SUPPLIER_RATING_CHOICES = [
    (1, '1 - Poor'),
    (2, '2 - Below Average'),
    (3, '3 - Average'),
    (4, '4 - Good'),
    (5, '5 - Excellent'),
]

# ============================================================================
# GENERAL CHOICES
# ============================================================================

GENDER_CHOICES = [
    ('Male', 'Male'),
    ('Female', 'Female'),
    ('Other', 'Other'),
]

ACTIVE_STATUS_CHOICES = [
    (True, 'Active'),
    (False, 'Inactive'),
]

APPROVAL_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('APPROVED', 'Approved'),
    ('REJECTED', 'Rejected'),
    ('CANCELLED', 'Cancelled'),
]

PRIORITY_CHOICES = [
    ('LOW', 'Low'),
    ('MEDIUM', 'Medium'),
    ('HIGH', 'High'),
    ('URGENT', 'Urgent'),
]

# ============================================================================
# APPOINTMENT & CONSULTATION CHOICES
# ============================================================================

APPOINTMENT_STATUS_CHOICES = [
    ('SCHEDULED', 'Scheduled'),
    ('CONFIRMED', 'Confirmed'),
    ('IN_PROGRESS', 'In Progress'),
    ('COMPLETED', 'Completed'),
    ('CANCELLED', 'Cancelled'),
    ('NO_SHOW', 'No Show'),
    ('DISPENSED', 'Dispensed'),
]

CONSULTATION_TYPE_CHOICES = [
    ('FIRST_VISIT', 'First Visit'),
    ('FOLLOW_UP', 'Follow Up'),
    ('EMERGENCY', 'Emergency'),
    ('ROUTINE', 'Routine'),
]

# ============================================================================
# LAB & TEST CHOICES
# ============================================================================

TEST_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('IN_PROGRESS', 'In Progress'),
    ('COMPLETED', 'Completed'),
    ('CANCELLED', 'Cancelled'),
]

SAMPLE_STATUS_CHOICES = [
    ('COLLECTED', 'Collected'),
    ('IN_LAB', 'In Lab'),
    ('TESTED', 'Tested'),
    ('REJECTED', 'Rejected'),
]

# Lab Test Order Status (for External Lab Management)
LAB_ORDER_STATUS_CHOICES = [
    ('ORDERED', 'Ordered'),                     # Order created, not sent yet
    ('SENT', 'Sent to External Lab'),          # Sample sent to external lab
    ('RECEIVED', 'Results Received'),          # PDF received and uploaded
    ('COMPLETED', 'Completed'),                # Fully processed and delivered
    ('CANCELLED', 'Cancelled'),                # Order cancelled
]

# Lab Order Payment Status (supports partial payments)
LAB_PAYMENT_STATUS_CHOICES = [
    ('UNPAID', 'Unpaid'),                      # No payment made (₹0)
    ('PARTIALLY_PAID', 'Partially Paid'),      # Some amount paid (advance)
    ('PAID', 'Fully Paid'),                    # Full amount paid
    ('REFUNDED', 'Refunded'),                  # Payment refunded
]

# ============================================================================
# BILLING CHOICES
# ============================================================================

BILL_TYPE_CHOICES = [
    ('OP', 'Out Patient'),
    ('IP', 'In Patient'),
    ('PHARMACY', 'Pharmacy'),
    ('LAB', 'Laboratory'),
    ('EMERGENCY', 'Emergency'),
]

DISCOUNT_TYPE_CHOICES = [
    ('PERCENTAGE', 'Percentage'),
    ('FIXED', 'Fixed Amount'),
]

# ============================================================================
# CREDIT NOTE & RETURN CHOICES
# ============================================================================

CREDIT_NOTE_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('APPROVED', 'Approved'),
    ('REJECTED', 'Rejected'),
    ('PROCESSED', 'Processed'),
]

RETURN_REASON_CHOICES = [
    ('EXPIRED', 'Expired'),
    ('DAMAGED', 'Damaged'),
    ('NEAR_EXPIRY', 'Near Expiry'),
    ('OVERSTOCKED', 'Overstocked'),
    ('QUALITY_ISSUE', 'Quality Issue'),
    ('WRONG_ITEM', 'Wrong Item Received'),
    ('PATIENT_RETURN', 'Patient Return'),
    ('OTHER', 'Other'),
]

# ============================================================================
# TAX CHOICES
# ============================================================================

GST_TYPE_CHOICES = [
    ('CGST_SGST', 'CGST + SGST'),
    ('IGST', 'IGST'),
    ('EXEMPT', 'Exempt'),
]

GST_RATE_CHOICES = [
    (0, '0%'),
    (5, '5%'),
    (12, '12%'),
    (18, '18%'),
    (28, '28%'),
]

# ============================================================================
# OUTLET/BRANCH CHOICES (For Multi-location Support)
# ============================================================================

OUTLET_TYPE_CHOICES = [
    ('MAIN', 'Main Branch'),
    ('SUB', 'Sub Branch'),
    ('WAREHOUSE', 'Warehouse'),
    ('SATELLITE', 'Satellite Pharmacy'),
]

# ============================================================================
# CONSTANTS (Non-choice values)
# ============================================================================

# Auto-generation formats
SUPPLIER_CODE_FORMAT = "SUP-{:04d}"
PURCHASE_ORDER_FORMAT = "PO-{date}-{seq:04d}"
GRN_NUMBER_FORMAT = "GRN-{date}-{seq:04d}"
RETURN_NUMBER_FORMAT = "PRET-{:06d}"
CREDIT_NOTE_FORMAT = "CN-{date}-{seq:04d}"

# Stock thresholds
DEFAULT_REORDER_LEVEL = 50
DEFAULT_REORDER_QUANTITY = 100
DEFAULT_MAX_STOCK_LEVEL = 500
DEFAULT_LEAD_TIME_DAYS = 7
NEAR_EXPIRY_DAYS = 90  # 3 months

# Credit defaults
DEFAULT_CREDIT_DAYS = 30
MAX_CREDIT_DAYS = 180

# GST defaults
DEFAULT_GST_RATE = 12
DEFAULT_CGST_RATE = 6
DEFAULT_SGST_RATE = 6

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
