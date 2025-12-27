"""
Hospital Information System - Unique ID Generation & Number Utilities
====================================================================

Author: Athul Gopan
Created: 2025
Module: Unique Identifier Generation and Number Conversion

This module provides utility functions for:
1. Generating unique sequential IDs for various entities (patients, appointments, bills)
2. Converting numbers to words (for bill generation in Indian number system)

ID Generation Functions:
    - get_next_patient_id(): Generates patient IDs (PAT-XXX)
    - get_next_appointment_id(): Generates appointment IDs (APPT-XXX)
    - get_next_bill_id(): Generates patient bill IDs (BIL-XXX)
    - get_next_pharma_bill_id(): Generates pharmacy bill IDs (PH-YYYYMM-XXX)
    - get_next_lab_bill_id(): Generates lab bill IDs (LB-YYYYMM-XXX)

Number Conversion Functions:
    - num_to_words(): Converts numbers to Indian currency words format
"""

from apps.data_hub.models import *
from datetime import datetime


# ============================================================================
# UNIQUE ID GENERATION FUNCTIONS
# ============================================================================

# Secret offset for patient ID generation to avoid starting from 1
# This makes patient IDs less predictable for security purposes
SECRET_OFFSET = 100000


def get_next_patient_id():
    """
    Generate the next sequential patient ID.

    Patient IDs follow the format: PAT-XXX (e.g., PAT-001, PAT-002)
    The first patient ID starts from SECRET_OFFSET + 1 for security.

    Returns:
        str: Next patient ID in format "PAT-XXX" where XXX is zero-padded to 3 digits

    Example:
        >>> get_next_patient_id()
        'PAT-100001'
    """
    # Get the most recently created patient
    last_patient = PatientRegistration.objects.order_by('-id').first()

    if last_patient:
        # Extract number from existing ID (e.g., "PAT-100001" -> 100001) and increment
        next_num = int(last_patient.patient_id.split('-')[1]) + 1
    else:
        # First patient in the system - start from SECRET_OFFSET + 1
        next_num = SECRET_OFFSET + 1

    # Format: PAT-XXX with zero padding for 3 digits minimum
    return f"PAT-{str(next_num).zfill(3)}"


def get_next_appointment_id():
    """
    Generate the next sequential appointment ID.

    Appointment IDs follow the format: APPT-XXX (e.g., APPT-001, APPT-002)

    Returns:
        str: Next appointment ID in format "APPT-XXX" where XXX is zero-padded to 3 digits

    Example:
        >>> get_next_appointment_id()
        'APPT-001'
    """
    # Get the most recently created appointment
    last_appointment = Appointment.objects.order_by('-id').first()

    if last_appointment:
        # Extract number from existing ID and increment
        next_num = int(last_appointment.appointment_id.split('-')[1]) + 1
    else:
        # First appointment - start from 1
        next_num = 1

    # Format: APPT-XXX with zero padding for 3 digits minimum
    return f"APPT-{str(next_num).zfill(3)}"


def get_next_bill_id(appointment):
    """
    Generate the next patient bill ID or return existing bill number for an appointment.

    This function checks if a bill already exists for the given appointment.
    If exists, returns the existing bill number. Otherwise, generates a new one.

    Bill IDs follow the format: BIL-XXX (e.g., BIL-001, BIL-002)

    Args:
        appointment: Appointment object for which to generate/retrieve bill ID

    Returns:
        str: Bill ID in format "BIL-XXX" where XXX is zero-padded to 3 digits

    Example:
        >>> appointment = Appointment.objects.get(id=1)
        >>> get_next_bill_id(appointment)
        'BIL-001'
    """
    # Check if a bill already exists for this appointment
    try:
        existing_bill = PatientBill.objects.get(appointment=appointment)
        return existing_bill.bill_number
    except PatientBill.DoesNotExist:
        # No existing bill - continue to generate new one
        pass

    # Get the most recently created bill
    last_bill = PatientBill.objects.order_by('-id').first()

    if last_bill and last_bill.bill_number.startswith('BIL-'):
        # Extract number from existing bill ID and increment
        last_number = int(last_bill.bill_number.split('-')[1])
        next_number = last_number + 1
    else:
        # First bill - start from 1
        next_number = 1

    # Format: BIL-XXX with zero padding for 3 digits minimum
    return f"BIL-{str(next_number).zfill(3)}"


def get_next_pharma_bill_id():
    """
    Generate the next pharmacy bill ID with period-based sequencing.

    Pharmacy bill IDs follow the format: PH-YYYYMM-XXX
    - PH: Pharmacy prefix
    - YYYYMM: Year and month (e.g., 202501 for January 2025)
    - XXX: Sequential number for that month (zero-padded to 3 digits)

    The sequence resets each month, making it easy to track monthly billing.

    Returns:
        str: Next pharmacy bill ID in format "PH-YYYYMM-XXX"

    Example:
        >>> get_next_pharma_bill_id()  # Called in January 2025
        'PH-202501-001'
    """
    # Get current year and month (e.g., "202501" for January 2025)
    current_period = datetime.now().strftime('%Y%m')

    # Find the last bill for the current month
    last_bill = PharmacyBilling.objects.filter(
        bill_number__startswith=f"PH-{current_period}"
    ).order_by('-bill_number').first()

    if last_bill:
        try:
            # Extract sequence number from the last bill and increment
            # Example: "PH-202501-005" -> extract "005" -> increment to 6
            sequence_str = last_bill.bill_number.split('-')[-1]
            sequence = int(sequence_str) + 1
        except (ValueError, IndexError):
            # Handle malformed bill numbers - start from 1
            sequence = 1
    else:
        # First bill for this month - start from 1
        sequence = 1

    # Format: PH-YYYYMM-XXX with zero padding for 3 digits minimum
    return f"PH-{current_period}-{str(sequence).zfill(3)}"


def get_next_lab_bill_id():
    """
    Generate the next laboratory bill ID with period-based sequencing.

    Lab bill IDs follow the format: LB-YYYYMM-XXX
    - LB: Laboratory prefix
    - YYYYMM: Year and month (e.g., 202501 for January 2025)
    - XXX: Sequential number for that month (zero-padded to 3 digits)

    The sequence resets each month, making it easy to track monthly billing.

    Returns:
        str: Next lab bill ID in format "LB-YYYYMM-XXX"

    Example:
        >>> get_next_lab_bill_id()  # Called in January 2025
        'LB-202501-001'
    """
    # Get current year and month (e.g., "202501" for January 2025)
    current_period = datetime.now().strftime('%Y%m')

    # Find the last bill for the current month
    last_bill = LabBilling.objects.filter(
        bill_number__startswith=f"LB-{current_period}"
    ).order_by('-bill_number').first()

    if last_bill:
        try:
            # Extract sequence number from the last bill and increment
            # Example: "LB-202501-005" -> extract "005" -> increment to 6
            sequence_str = last_bill.bill_number.split('-')[-1]
            sequence = int(sequence_str) + 1
        except (ValueError, IndexError):
            # Handle malformed bill numbers - start from 1
            sequence = 1
    else:
        # First bill for this month - start from 1
        sequence = 1

    # Format: LB-YYYYMM-XXX with zero padding for 3 digits minimum
    return f"LB-{current_period}-{str(sequence).zfill(3)}"




# ============================================================================
# NUMBER TO WORDS CONVERSION (INDIAN CURRENCY FORMAT)
# ============================================================================

def num_to_words(num):
    """
    Convert a numeric amount to words in Indian currency format.

    This function converts decimal numbers to their word representation
    following the Indian numbering system (Crore, Lakh, Thousand) and
    currency format (Rupees and Paise).

    The Indian numbering system uses:
    - Crore: 10,000,000 (1,00,00,000)
    - Lakh: 100,000 (1,00,000)
    - Thousand: 1,000

    Args:
        num (float): The number to convert (supports decimals for paise)

    Returns:
        str: Number in words format (e.g., "One Thousand Two Hundred Rupees and Fifty Paise")

    Examples:
        >>> num_to_words(1250.50)
        'One Thousand Two Hundred Fifty Rupees and Fifty Paise'

        >>> num_to_words(10000000)
        'One Crore Rupees'

        >>> num_to_words(0)
        'Zero'
    """

    def _convert_under_thousand(n):
        """
        Helper function to convert numbers under 1000 to words.

        This handles the conversion of numbers from 0-999 into their
        word representation.

        Args:
            n (int): Number between 0 and 999

        Returns:
            str: Word representation of the number
        """
        # Words for numbers 0-19
        ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten',
                'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']

        # Words for tens (20, 30, 40, etc.)
        tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

        if n < 20:
            # Direct lookup for 0-19
            return ones[n]
        elif n < 100:
            # Combine tens and ones (e.g., "Twenty Five")
            return tens[n // 10] + (' ' + ones[n % 10] if n % 10 != 0 else '')
        else:
            # Handle hundreds (e.g., "Two Hundred and Thirty Five")
            return ones[n // 100] + ' Hundred' + (' and ' + _convert_under_thousand(n % 100) if n % 100 != 0 else '')

    # Handle zero as special case
    if num == 0:
        return 'Zero'

    # Separate rupees and paise (decimal part)
    rupees = int(num)
    paise = int(round((num - rupees) * 100))

    result = ''

    # ========================================================================
    # Process rupees part using Indian numbering system
    # ========================================================================
    if rupees > 0:
        # Break down the number into Indian denominations
        crore = rupees // 10000000      # Crore (10 million)
        rupees %= 10000000

        lakh = rupees // 100000          # Lakh (100 thousand)
        rupees %= 100000

        thousand = rupees // 1000        # Thousand
        rupees %= 1000

        # Build the rupees part of the string
        if crore > 0:
            result += _convert_under_thousand(crore) + ' Crore '

        if lakh > 0:
            result += _convert_under_thousand(lakh) + ' Lakh '

        if thousand > 0:
            result += _convert_under_thousand(thousand) + ' Thousand '

        if rupees > 0:
            result += _convert_under_thousand(rupees)

        # Add "Rupees" suffix
        result += ' Rupees'

    # ========================================================================
    # Process paise part (decimal/fractional amount)
    # ========================================================================
    if paise > 0:
        result += ' and ' + _convert_under_thousand(paise) + ' Paise'

    return result.strip()







