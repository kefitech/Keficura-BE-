"""
Hospital Information System - Pharmacy Module Views
====================================================

Author: Athul Gopan
Created: 2025
Module: Pharmacy & Billing APIs

This module contains all API endpoints for:
1. Pharmacist Profile Management
2. Medication & Stock Management (OPD Pharmacy)
3. Doctor Consultation & Prescription Management
4. Medication Dispensing (FIFO Logic)
5. Patient Billing & Payment History
6. Laboratory Services & Billing
7. Lab Test Configuration (Departments, Categories, Parameters)

API Structure:
    - All views inherit from APIView
    - Transactions are wrapped with @transaction.atomic
    - Error handling follows standardized response format
    - Permission classes are configured per view
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction, IntegrityError
from apps.data_hub.models import *
from .serializers import *
from utils.auth_helper import *
from django.utils import timezone
from django.db.models import Sum, F, Value, IntegerField, Prefetch, Q
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta
import pytz
from decimal import Decimal, InvalidOperation
from collections import defaultdict
from utils.auth_unique_id import *
from utils.email_helper import *
import calendar
from django.core.exceptions import ValidationError
from django.db.models.functions import Coalesce

logger = logging.getLogger(__name__)


# ============================================================================
# SECTION 0: SUPPLIER MANAGEMENT APIs
# ============================================================================

class SupplierView(APIView):
    """
    Supplier Management API

    Endpoints:
        POST /api/pharmacy/suppliers/ - Create new supplier
        GET /api/pharmacy/suppliers/ - List all suppliers with filtering
        GET /api/pharmacy/suppliers/<id>/ - Get supplier details
        PATCH /api/pharmacy/suppliers/<id>/ - Update supplier
        DELETE /api/pharmacy/suppliers/<id>/ - Delete/Deactivate supplier

    Features:
        - Auto-generate supplier code (SUP-0001, SUP-0002, etc.)
        - Filter by active status, payment type, supplier type
        - Search by name or code
        - Pagination support
        - Validation for GSTIN, phone, credit terms
    """

 
    def post(self, request):
        """
        Create a new supplier

        Request Body:
            {
                "name": "MediPharma Distributors",
                "supplier_type": "DISTRIBUTOR",
                "phone": "9876543210",
                "email": "sales@medipharma.com",
                "address": "123, Mumbai",
                "gstin": "27ABCDE1234F1Z5",
                "payment_type": "CREDIT",
                "credit_days": 30,
                "credit_limit": 500000.00
            

        Returns:
            201: Supplier created successfully
            400: Validation error
        """
        try:
            # Add created_by from authenticate
            data = request.data.copy()

            serializer = SupplierSerializer(data=data)

            if serializer.is_valid():
                # Save with created_by
                supplier = serializer.save(created_by=request.user)

                logger.info(f"Supplier created: {supplier.code} - {supplier.name} by {request.user.username}")

                return Response({
                    'message': 'Supplier created successfully',
                    'data': SupplierSerializer(supplier).data
                }, status=status.HTTP_201_CREATED)

            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error creating supplier: {str(e)}")
            return Response({
                'error': 'Failed to create supplier',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

 
    def get(self, request, supplier_id=None):
        """
        Get supplier details or list suppliers

        Query Parameters (for list):
            - is_active: Filter by active status (true/false)
            - payment_type: Filter by payment type (CASH, CREDIT, BOTH)
            - supplier_type: Filter by supplier type
            - search: Search by name or code
            - page: Page number (default: 1)
            - page_size: Items per page (default: 20, max: 100)

        Returns:
            200: Supplier details or list
            404: Supplier not found
        """
        try:
            # Get single supplier by ID
            if supplier_id:
                try:
                    supplier = Supplier.objects.get(id=supplier_id)
                    return Response({
                        'data': SupplierSerializer(supplier).data
                    }, status=status.HTTP_200_OK)
                except Supplier.DoesNotExist:
                    return Response({
                        'error': 'Supplier not found'
                    }, status=status.HTTP_404_NOT_FOUND)

            # List suppliers with filtering
            queryset = Supplier.objects.all().order_by('-created_on')

            # Filter by active status
            is_active = request.GET.get('is_active')
            if is_active is not None:
                is_active_bool = is_active.lower() == 'true'
                queryset = queryset.filter(is_active=is_active_bool)

            # Filter by payment type
            payment_type = request.GET.get('payment_type')
            if payment_type:
                queryset = queryset.filter(payment_type=payment_type)

            # Filter by supplier type
            supplier_type = request.GET.get('supplier_type')
            if supplier_type:
                queryset = queryset.filter(supplier_type=supplier_type)

            # Search by name or code
            search = request.GET.get('search')
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) | Q(code__icontains=search)
                )

            # Pagination
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)

            total_count = queryset.count()
            start = (page - 1) * page_size
            end = start + page_size

            suppliers = queryset[start:end]

            return Response({
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size,
                'data': SupplierListSerializer(suppliers, many=True).data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching suppliers: {str(e)}")
            return Response({
                'error': 'Failed to fetch suppliers',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

   
    def patch(self, request, supplier_id):
        """
        Update supplier details

        Request Body (partial update):
            {
                "phone": "9876543299",
                "credit_limit": 600000.00,
                "rating": 4
            }

        Returns:
            200: Supplier updated successfully
            404: Supplier not found
            400: Validation error
        """
        try:
            try:
                supplier = Supplier.objects.get(id=supplier_id)
            except Supplier.DoesNotExist:
                return Response({
                    'error': 'Supplier not found'
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = SupplierSerializer(supplier, data=request.data, partial=True)

            if serializer.is_valid():
                # Save with updated_by
                supplier = serializer.save(updated_by=request.user, updated_on=timezone.now())

                logger.info(f"Supplier updated: {supplier.code} by {request.user.username}")

                return Response({
                    'message': 'Supplier updated successfully',
                    'data': SupplierSerializer(supplier).data
                }, status=status.HTTP_200_OK)

            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error updating supplier: {str(e)}")
            return Response({
                'error': 'Failed to update supplier',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

 
    def delete(self, request, supplier_id):
        """
        Delete/Deactivate supplier (soft delete)

        Returns:
            200: Supplier deactivated successfully
            404: Supplier not found
        """
        try:
            try:
                supplier = Supplier.objects.get(id=supplier_id)
            except Supplier.DoesNotExist:
                return Response({
                    'error': 'Supplier not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Soft delete - set is_active to False
            supplier.is_active = False
            supplier.updated_by = request.user
            supplier.updated_on = timezone.now()
            supplier.save()

            logger.info(f"Supplier deactivated: {supplier.code} by {request.user.username}")

            return Response({
                'message': 'Supplier deactivated successfully',
                'supplier_code': supplier.code
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error deleting supplier: {str(e)}")
            return Response({
                'error': 'Failed to delete supplier',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SupplierSearchView(APIView):
    """
    Supplier Search API (Quick search for dropdowns)

    Endpoint:
        GET /api/pharmacy/suppliers/search/?q=<search_term>

    Features:
        - Fast search by name or code
        - Returns minimal data for dropdown selections
        - Only active suppliers
    """

  
    def get(self, request):
        """
        Search suppliers by name or code

        Query Parameters:
            - q: Search term (required)

        Returns:
            200: List of matching suppliers
        """
        try:
            search_term = request.GET.get('q', '').strip()

            if not search_term:
                return Response({
                    'error': 'Search term is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Search active suppliers only
            suppliers = Supplier.objects.filter(
                Q(name__icontains=search_term) | Q(code__icontains=search_term),
                is_active=True
            ).order_by('name')[:20]  # Limit to 20 results

            results = [{
                'id': s.id,
                'code': s.code,
                'name': s.name,
                'phone': s.phone,
                'payment_type': s.payment_type,
                'credit_days': s.credit_days
            } for s in suppliers]

            return Response({
                'data': results
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error searching suppliers: {str(e)}")
            return Response({
                'error': 'Failed to search suppliers',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# PURCHASE ORDER MANAGEMENT APIs
# ============================================================================

class PurchaseOrderView(APIView):
    """
    Purchase Order Management API

    Endpoints:
        POST /api/pharmacy/purchase-orders/ - Create new PO
        GET /api/pharmacy/purchase-orders/ - List all POs with filtering
        GET /api/pharmacy/purchase-orders/<id>/ - Get PO details
        PATCH /api/pharmacy/purchase-orders/<id>/ - Update PO
        DELETE /api/pharmacy/purchase-orders/<id>/ - Delete/Deactivate PO

    Features:
        - Auto-generate PO number (PO-YYYYMMDD-XXXX)
        - Filter by supplier, status, date range
        - Search by PO number
        - Pagination support
        - Calculate received/pending amounts
        - Track linked GRNs
    """

    
    def post(self, request):
        """
        Create a new purchase order

        Request Body:
            {
                "supplier": 1,
                "order_date": "2025-12-01",
                "expected_delivery_date": "2025-12-08",
                "total_amount": 125000.00,
                "notes": "Urgent order"
            }

        Returns:
            201: PO created successfully
            400: Validation error
        """
        try:
            serializer = PurchaseOrderSerializer(data=request.data)

            if serializer.is_valid():
                # Save with created_by
                po = serializer.save(created_by=request.user)

                logger.info(f"Purchase Order created: {po.po_number} by {request.user.username}")

                return Response({
                    'message': 'Purchase order created successfully',
                    'data': PurchaseOrderSerializer(po).data
                }, status=status.HTTP_201_CREATED)

            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error creating purchase order: {str(e)}")
            return Response({
                'error': 'Failed to create purchase order',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, po_id=None):
        """
        Get PO details or list POs

        Query Parameters (for list):
            - supplier_id: Filter by supplier
            - status: Filter by status (PENDING, APPROVED, etc.)
            - order_date_from: From date
            - order_date_to: To date
            - search: Search by PO number
            - page: Page number (default: 1)
            - page_size: Items per page (default: 20)

        Returns:
            200: PO details or list
            404: PO not found
        """
        try:
            # Get single PO by ID
            if po_id:
                try:
                    po = PurchaseOrder.objects.select_related('supplier').get(id=po_id)
                    return Response({
                        'data': PurchaseOrderSerializer(po).data
                    }, status=status.HTTP_200_OK)
                except PurchaseOrder.DoesNotExist:
                    return Response({
                        'error': 'Purchase order not found'
                    }, status=status.HTTP_404_NOT_FOUND)

            # List POs with filtering
            queryset = PurchaseOrder.objects.select_related('supplier').all().order_by('-order_date', '-created_on')

            # Filter by supplier
            supplier_id = request.GET.get('supplier_id')
            if supplier_id:
                queryset = queryset.filter(supplier_id=supplier_id)

            # Filter by status
            status_filter = request.GET.get('status')
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            # Filter by date range
            order_date_from = request.GET.get('order_date_from')
            if order_date_from:
                queryset = queryset.filter(order_date__gte=order_date_from)

            order_date_to = request.GET.get('order_date_to')
            if order_date_to:
                queryset = queryset.filter(order_date__lte=order_date_to)

            # Search by PO number
            search = request.GET.get('search')
            if search:
                queryset = queryset.filter(po_number__icontains=search)

            # Filter by active status
            is_active = request.GET.get('is_active')
            if is_active is not None:
                is_active_bool = is_active.lower() == 'true'
                queryset = queryset.filter(is_active=is_active_bool)

            # Pagination
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)

            total_count = queryset.count()
            start = (page - 1) * page_size
            end = start + page_size

            pos = queryset[start:end]

            return Response({
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size,
                'data': PurchaseOrderListSerializer(pos, many=True).data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching purchase orders: {str(e)}")
            return Response({
                'error': 'Failed to fetch purchase orders',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, po_id):
        """
        Update purchase order

        Request Body (partial update):
            {
                "expected_delivery_date": "2025-12-10",
                "total_amount": 150000.00,
                "status": "APPROVED"
            }

        Returns:
            200: PO updated successfully
            404: PO not found
            400: Validation error
        """
        try:
            try:
                po = PurchaseOrder.objects.get(id=po_id)
            except PurchaseOrder.DoesNotExist:
                return Response({
                    'error': 'Purchase order not found'
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = PurchaseOrderSerializer(po, data=request.data, partial=True)

            if serializer.is_valid():
                # Save with updated_by
                po = serializer.save(updated_by=request.user, updated_on=timezone.now())

                logger.info(f"Purchase Order updated: {po.po_number} by {request.user.username}")

                return Response({
                    'message': 'Purchase order updated successfully',
                    'data': PurchaseOrderSerializer(po).data
                }, status=status.HTTP_200_OK)

            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error updating purchase order: {str(e)}")
            return Response({
                'error': 'Failed to update purchase order',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, po_id):
        """
        Delete/Deactivate purchase order (soft delete)

        Returns:
            200: PO deactivated successfully
            404: PO not found
        """
        try:
            try:
                po = PurchaseOrder.objects.get(id=po_id)
            except PurchaseOrder.DoesNotExist:
                return Response({
                    'error': 'Purchase order not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Soft delete
            po.is_active = False
            po.status = 'CANCELLED'
            po.updated_by = request.user
            po.updated_on = timezone.now()
            po.save()

            logger.info(f"Purchase Order cancelled: {po.po_number} by {request.user.username}")

            return Response({
                'message': 'Purchase order cancelled successfully',
                'po_number': po.po_number
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error deleting purchase order: {str(e)}")
            return Response({
                'error': 'Failed to delete purchase order',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PurchaseOrderApproveView(APIView):
    """
    Approve Purchase Order API

    Endpoint:
        POST /api/pharmacy/purchase-orders/<id>/approve/

    Features:
        - Change status to APPROVED
        - Log approval action
    """

    def post(self, request, po_id):
        """
        Approve a purchase order

        Returns:
            200: PO approved successfully
            404: PO not found
            400: Invalid status for approval
        """
        try:
            try:
                po = PurchaseOrder.objects.get(id=po_id)
            except PurchaseOrder.DoesNotExist:
                return Response({
                    'error': 'Purchase order not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Check if PO can be approved
            if po.status in ['COMPLETED', 'CANCELLED']:
                return Response({
                    'error': f'Cannot approve purchase order with status {po.status}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Approve PO
            po.status = 'APPROVED'
            po.updated_by = request.user
            po.updated_on = timezone.now()
            po.save()

            logger.info(f"Purchase Order approved: {po.po_number} by {request.user.username}")

            return Response({
                'message': 'Purchase order approved successfully',
                'po_number': po.po_number,
                'status': po.status
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error approving purchase order: {str(e)}")
            return Response({
                'error': 'Failed to approve purchase order',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# PURCHASE ENTRY (GRN) MANAGEMENT APIs
# ============================================================================

class PurchaseEntryView(APIView):
    """
    Purchase Entry (GRN) Management API

    Endpoints:
        POST /api/pharmacy/purchase-entries/ - Create new GRN with items
        GET /api/pharmacy/purchase-entries/ - List all GRNs with filtering
        GET /api/pharmacy/purchase-entries/<id>/ - Get GRN details
        PATCH /api/pharmacy/purchase-entries/<id>/ - Update GRN
        DELETE /api/pharmacy/purchase-entries/<id>/ - Delete/Deactivate GRN

    Features:
        - Auto-generate GRN number (GRN-YYYYMMDD-XXXX)
        - Create nested purchase items
        - Auto-calculate GST and totals
        - Auto-create MedicationStock entries
        - Update PurchaseOrder status
        - Filter by supplier, PO, date range, payment status
        - Pagination support
    """

    @transaction.atomic
    def post(self, request):
        """
        Create a new GRN with items

        Request Body:
            {
                "supplier": 1,
                "purchase_order": 1,
                "invoice_number": "INV-2024-12345",
                "invoice_date": "2025-11-30",
                "received_date": "2025-12-01",
                "payment_mode": "CREDIT",
                "items": [
                    {
                        "medication": 5,
                        "batch_number": "BATCH-2024-12345",
                        "expiry_date": "2027-11-30",
                        "quantity": 1000,
                        "free_quantity": 100,
                        "mrp": 10.00,
                        "purchase_price": 6.00,
                        "ptr": 7.50,
                        "cgst_percent": 6.00,
                        "sgst_percent": 6.00
                    }
                ]
            }

        Returns:
            201: GRN created successfully with auto-created stock
            400: Validation error
        """
        try:
            # Add created_by
            data = request.data.copy()

            serializer = PurchaseEntrySerializer(data=data, context={'request': request})

            if serializer.is_valid():
                # Save with created_by (auto-creates items and stock)
                grn = serializer.save(created_by=request.user)

                logger.info(f"GRN created: {grn.grn_number} with {grn.purchase_items.count()} items by {request.user.username}")

                return Response({
                    'message': 'Purchase entry (GRN) created successfully',
                    'data': PurchaseEntrySerializer(grn).data
                }, status=status.HTTP_201_CREATED)

            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error creating GRN: {str(e)}")
            return Response({
                'error': 'Failed to create purchase entry',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, grn_id=None):
        """
        Get GRN details or list GRNs

        Query Parameters (for list):
            - supplier_id: Filter by supplier
            - purchase_order_id: Filter by PO
            - payment_status: Filter by payment status
            - invoice_number: Search by invoice number
            - received_date_from: From date
            - received_date_to: To date
            - page: Page number (default: 1)
            - page_size: Items per page (default: 20)

        Returns:
            200: GRN details or list
            404: GRN not found
        """
        try:
            # Get single GRN by ID
            if grn_id:
                try:
                    grn = PurchaseEntry.objects.select_related(
                        'supplier', 'purchase_order'
                    ).prefetch_related('purchase_items__medication').get(id=grn_id)

                    return Response({
                        'data': PurchaseEntrySerializer(grn).data
                    }, status=status.HTTP_200_OK)
                except PurchaseEntry.DoesNotExist:
                    return Response({
                        'error': 'Purchase entry not found'
                    }, status=status.HTTP_404_NOT_FOUND)

            # List GRNs with filtering
            queryset = PurchaseEntry.objects.select_related(
                'supplier', 'purchase_order'
            ).all().order_by('-received_date', '-created_on')

            # Filter by supplier
            supplier_id = request.GET.get('supplier_id')
            if supplier_id:
                queryset = queryset.filter(supplier_id=supplier_id)

            # Filter by purchase order
            purchase_order_id = request.GET.get('purchase_order_id')
            if purchase_order_id:
                queryset = queryset.filter(purchase_order_id=purchase_order_id)

            # Filter by payment status
            payment_status = request.GET.get('payment_status')
            if payment_status:
                queryset = queryset.filter(payment_status=payment_status)

            # Search by invoice number
            invoice_number = request.GET.get('invoice_number')
            if invoice_number:
                queryset = queryset.filter(invoice_number__icontains=invoice_number)

            # Filter by date range
            received_date_from = request.GET.get('received_date_from')
            if received_date_from:
                queryset = queryset.filter(received_date__gte=received_date_from)

            received_date_to = request.GET.get('received_date_to')
            if received_date_to:
                queryset = queryset.filter(received_date__lte=received_date_to)

            # Filter by active status
            is_active = request.GET.get('is_active')
            if is_active is not None:
                is_active_bool = is_active.lower() == 'true'
                queryset = queryset.filter(is_active=is_active_bool)

            # Pagination
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)

            total_count = queryset.count()
            start = (page - 1) * page_size
            end = start + page_size

            grns = queryset[start:end]

            return Response({
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size,
                'data': PurchaseEntryListSerializer(grns, many=True).data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching GRNs: {str(e)}")
            return Response({
                'error': 'Failed to fetch purchase entries',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @transaction.atomic
    def patch(self, request, grn_id):
        """
        Update GRN - Full edit for PENDING, limited edit for APPROVED/REJECTED

        For PENDING GRNs:
            - Can edit ALL fields including items (add/remove/modify)
            - Stock entries will be updated accordingly

        For APPROVED/REJECTED GRNs:
            - Can only edit: payment_status, payment_mode, payment_date, notes

        Request Body (for PENDING GRN):
            {
                "invoice_number": "INV-123",
                "invoice_date": "2025-12-15",
                "received_date": "2025-12-15",
                "payment_status": "PAID",
                "payment_mode": "UPI",
                "notes": "Updated notes",
                "items": [
                    {
                        "medication": 5,
                        "batch_number": "BATCH-001",
                        "expiry_date": "2027-12-31",
                        "quantity": 1000,
                        "free_quantity": 100,
                        "mrp": 10.00,
                        "purchase_price": 6.00,
                        "ptr": 7.50,
                        "cgst_percent": 6.00,
                        "sgst_percent": 6.00
                    }
                ]
            }

        Returns:
            200: GRN updated successfully
            404: GRN not found
            400: Validation error or not allowed to edit
        """
        try:
            try:
                grn = PurchaseEntry.objects.prefetch_related('purchase_items', 'stock_entries').get(id=grn_id)
            except PurchaseEntry.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'Purchase entry not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Check GRN status
            if grn.status == 'PENDING':
                # FULL EDIT ALLOWED for PENDING GRNs
                items_data = request.data.get('items', None)

                # Convert date strings to date objects for GRN fields
                from datetime import datetime
                date_fields = ['invoice_date', 'received_date', 'payment_date']
                for date_field in date_fields:
                    if date_field in request.data and isinstance(request.data.get(date_field), str):
                        try:
                            request.data[date_field] = datetime.strptime(request.data[date_field], '%Y-%m-%d').date()
                        except (ValueError, TypeError):
                            pass  # Keep original value if conversion fails

                # Convert numeric strings to Decimal for GRN-level fields
                if 'discount_amount' in request.data and isinstance(request.data['discount_amount'], str):
                    request.data['discount_amount'] = Decimal(request.data['discount_amount']) if request.data['discount_amount'] else Decimal('0')

                # Update basic fields
                basic_fields = ['invoice_number', 'invoice_date', 'received_date',
                               'payment_status', 'payment_mode', 'payment_date',
                               'notes', 'discount_amount']

                for field in basic_fields:
                    if field in request.data:
                        setattr(grn, field, request.data[field])

                # If items are being updated, smartly update/create/delete items
                if items_data is not None:
                    # Get existing item IDs
                    existing_items = {item.id: item for item in grn.purchase_items.all()}
                    processed_item_ids = set()

                    # Process each item from request
                    for item_data in items_data:
                        item_id = item_data.pop('id', None)  # Extract ID if provided

                        # Convert date strings to date objects
                        if 'expiry_date' in item_data and isinstance(item_data['expiry_date'], str):
                            from datetime import datetime
                            item_data['expiry_date'] = datetime.strptime(item_data['expiry_date'], '%Y-%m-%d').date()

                        # Convert numeric strings to Decimal for proper calculations
                        numeric_fields = ['mrp', 'purchase_price', 'ptr', 'discount_percent',
                                         'discount_amount', 'cgst_percent', 'sgst_percent', 'igst_percent']
                        for field in numeric_fields:
                            if field in item_data and isinstance(item_data[field], str):
                                item_data[field] = Decimal(item_data[field]) if item_data[field] else Decimal('0')
                            elif field in item_data and item_data[field] is None:
                                item_data[field] = Decimal('0')

                        if item_id and item_id in existing_items:
                            # UPDATE existing item
                            purchase_item = existing_items[item_id]

                            # Update purchase item fields (handle medication ID properly)
                            medication_id = item_data.get('medication_id') or item_data.get('medication')

                            for field, value in item_data.items():
                                if field in ['medication', 'medication_id']:
                                    # Set using _id suffix for foreign key
                                    purchase_item.medication_id = value
                                else:
                                    setattr(purchase_item, field, value)
                            purchase_item.save()

                            # Update or create stock entry
                            total_qty = item_data['quantity'] + item_data.get('free_quantity', 0)

                            if hasattr(purchase_item, 'stock_entry') and purchase_item.stock_entry:
                                # UPDATE existing stock entry
                                stock_entry = purchase_item.stock_entry
                                stock_entry.medication_id = medication_id
                                stock_entry.batch_number = item_data['batch_number']
                                stock_entry.expiry_date = item_data['expiry_date']
                                stock_entry.quantity = total_qty
                                stock_entry.received_quantity = total_qty
                                stock_entry.received_date = grn.received_date
                                stock_entry.purchase_price = item_data['purchase_price']
                                stock_entry.selling_price = item_data.get('mrp', item_data['purchase_price'])
                                stock_entry.mrp = item_data.get('mrp')
                                stock_entry.ptr = item_data.get('ptr')
                                stock_entry.free_quantity = item_data.get('free_quantity', 0)
                                stock_entry.packing = item_data.get('packing')
                                stock_entry.cgst_percent = item_data.get('cgst_percent', 0)
                                stock_entry.sgst_percent = item_data.get('sgst_percent', 0)
                                stock_entry.igst_percent = item_data.get('igst_percent', 0)
                                stock_entry.margin_percent = purchase_item.margin_percent
                                stock_entry.is_verified = False  # Mark as unverified - needs re-approval
                                stock_entry.save()
                            else:
                                # CREATE new stock entry if it doesn't exist
                                stock_entry = MedicationStock.objects.create(
                                    medication_id=medication_id,
                                    batch_number=item_data['batch_number'],
                                    expiry_date=item_data['expiry_date'],
                                    quantity=total_qty,
                                    received_quantity=total_qty,
                                    received_date=grn.received_date,
                                    purchase_price=item_data['purchase_price'],
                                    selling_price=item_data.get('mrp', item_data['purchase_price']),
                                    mrp=item_data.get('mrp'),
                                    ptr=item_data.get('ptr'),
                                    supplier=grn.supplier.name,
                                    manufacturer=grn.supplier.name,
                                    purchase_entry=grn,
                                    purchase_item=purchase_item,
                                    free_quantity=item_data.get('free_quantity', 0),
                                    packing=item_data.get('packing'),
                                    cgst_percent=item_data.get('cgst_percent', 0),
                                    sgst_percent=item_data.get('sgst_percent', 0),
                                    igst_percent=item_data.get('igst_percent', 0),
                                    margin_percent=purchase_item.margin_percent,
                                    is_verified=False,
                                    created_by=request.user
                                )
                                # Link stock to purchase item
                                purchase_item.stock_entry = stock_entry
                                purchase_item.save()

                            processed_item_ids.add(item_id)
                            logger.info(f"Updated item {item_id} in GRN {grn.grn_number}")

                        else:
                            # CREATE new item
                            # Handle both 'medication' and 'medication_id' keys
                            medication_id = item_data.pop('medication_id', None) or item_data.pop('medication', None)

                            if not medication_id:
                                raise ValueError("medication or medication_id is required")

                            purchase_item = PurchaseItem.objects.create(
                                purchase_entry=grn,
                                medication_id=medication_id,
                                **item_data
                            )

                            # Create UNVERIFIED stock entry
                            total_qty = item_data['quantity'] + item_data.get('free_quantity', 0)

                            stock_entry = MedicationStock.objects.create(
                                medication_id=medication_id,
                                batch_number=item_data['batch_number'],
                                expiry_date=item_data['expiry_date'],
                                quantity=total_qty,
                                received_quantity=total_qty,
                                received_date=grn.received_date,
                                purchase_price=item_data['purchase_price'],
                                selling_price=item_data.get('mrp', item_data['purchase_price']),
                                mrp=item_data.get('mrp'),
                                ptr=item_data.get('ptr'),
                                supplier=grn.supplier.name,
                                manufacturer=grn.supplier.name,
                                purchase_entry=grn,
                                purchase_item=purchase_item,
                                free_quantity=item_data.get('free_quantity', 0),
                                packing=item_data.get('packing'),
                                cgst_percent=item_data.get('cgst_percent', 0),
                                sgst_percent=item_data.get('sgst_percent', 0),
                                igst_percent=item_data.get('igst_percent', 0),
                                margin_percent=purchase_item.margin_percent,
                                is_verified=False,  # Still unverified - needs re-approval
                                created_by=request.user
                            )

                            # Link stock to purchase item
                            purchase_item.stock_entry = stock_entry
                            purchase_item.save()

                            logger.info(f"Created new item in GRN {grn.grn_number}")

                    # DELETE items that were removed (not in the request)
                    items_to_delete = set(existing_items.keys()) - processed_item_ids
                    if items_to_delete:
                        for item_id in items_to_delete:
                            item = existing_items[item_id]
                            # Delete stock first
                            if hasattr(item, 'stock_entry') and item.stock_entry:
                                item.stock_entry.delete()
                            # Delete item
                            item.delete()
                            logger.info(f"Deleted removed item {item_id} from GRN {grn.grn_number}")

                grn.updated_by = request.user
                grn.updated_on = timezone.now()
                grn.calculate_totals()

                logger.info(f"GRN fully updated: {grn.grn_number} by {request.user.username}")

                return Response({
                    'status': 'success',
                    'message': 'GRN updated successfully. Please review and approve again.',
                    'data': PurchaseEntrySerializer(grn).data
                }, status=status.HTTP_200_OK)

            else:
                # LIMITED EDIT for APPROVED/REJECTED GRNs
                allowed_fields = ['payment_status', 'payment_mode', 'payment_date', 'notes']

                # Check if user is trying to edit items
                if 'items' in request.data:
                    return Response({
                        'status': 'error',
                        'message': f'Cannot edit items for {grn.get_status_display()} GRN. Only payment details can be updated.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Update only allowed fields
                updated = False
                for field in allowed_fields:
                    if field in request.data:
                        setattr(grn, field, request.data[field])
                        updated = True

                if updated:
                    grn.updated_by = request.user
                    grn.updated_on = timezone.now()
                    grn.save()

                    logger.info(f"GRN payment details updated: {grn.grn_number} by {request.user.username}")

                    return Response({
                        'status': 'success',
                        'message': 'Payment details updated successfully',
                        'data': PurchaseEntrySerializer(grn).data
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'status': 'error',
                        'message': 'No valid fields to update'
                    }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error updating GRN: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Failed to update purchase entry: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, grn_id):
        """
        Delete/Deactivate GRN (soft delete)
        Also deactivates related stock entries

        Returns:
            200: GRN deactivated successfully
            404: GRN not found
        """
        try:
            try:
                grn = PurchaseEntry.objects.get(id=grn_id)
            except PurchaseEntry.DoesNotExist:
                return Response({
                    'error': 'Purchase entry not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Soft delete GRN
            grn.is_active = False
            grn.updated_by = request.user
            grn.updated_on = timezone.now()
            grn.save()

            # Also deactivate related stock entries
            MedicationStock.objects.filter(purchase_entry=grn).update(is_active=False)

            logger.info(f"GRN deactivated: {grn.grn_number} by {request.user.username}")

            return Response({
                'message': 'Purchase entry deactivated successfully',
                'grn_number': grn.grn_number
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error deleting GRN: {str(e)}")
            return Response({
                'error': 'Failed to delete purchase entry',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PurchaseEntryBulkDetailsView(APIView):
    """
    Bulk GRN Details API

    Purpose:
        Fetch full details with calculations for multiple GRNs in a single request.
        Useful for comparing multiple GRNs or generating reports.

    Endpoint:
        POST /api/pharmacy/purchase-entries/bulk-details/

    Request Body:
        {
            "grn_ids": [123, 124, 125]
        }

    Response:
        {
            "status": "success",
            "count": 3,
            "data": [
                {
                    "id": 123,
                    "grn_number": "GRN-20251216-0001",
                    "calculation_summary": { ... },
                    "purchase_items": [ ... ],
                    ...
                }
            ],
            "not_found": []  // IDs that don't exist
        }
    """

    def post(self, request):
        """
        Get full details for multiple GRNs

        Request Body:
            {
                "grn_ids": [123, 124, 125]
            }

        Returns:
            200: List of GRN details with calculations
            400: Validation error (missing grn_ids, invalid format)
        """
        try:
            # Validate request
            grn_ids = request.data.get('grn_ids', [])

            if not grn_ids:
                return Response({
                    'status': 'error',
                    'message': 'grn_ids is required and must be a non-empty list'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not isinstance(grn_ids, list):
                return Response({
                    'status': 'error',
                    'message': 'grn_ids must be a list of integers'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate all IDs are integers
            try:
                grn_ids = [int(id) for id in grn_ids]
            except (ValueError, TypeError):
                return Response({
                    'status': 'error',
                    'message': 'All grn_ids must be valid integers'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Limit to prevent abuse
            if len(grn_ids) > 50:
                return Response({
                    'status': 'error',
                    'message': 'Maximum 50 GRNs can be fetched at once'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Fetch GRNs
            grns = PurchaseEntry.objects.select_related(
                'supplier', 'purchase_order', 'approved_by', 'created_by', 'updated_by'
            ).prefetch_related(
                'purchase_items__medication'
            ).filter(id__in=grn_ids)

            # Track found and not found IDs
            found_ids = list(grns.values_list('id', flat=True))
            not_found_ids = [id for id in grn_ids if id not in found_ids]

            # Serialize all GRNs
            serializer = PurchaseEntrySerializer(grns, many=True)

            # Calculate total amount across all GRNs
            total_amount = sum(
                Decimal(str(grn.total_amount)) for grn in grns
            )

            logger.info(f"Bulk GRN details fetched: {len(found_ids)} found, {len(not_found_ids)} not found by {request.user.username}")

            return Response({
                'status': 'success',
                'count': len(found_ids),
                'data': serializer.data,
                'total_amount': str(total_amount),
                'not_found': not_found_ids
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching bulk GRN details: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Failed to fetch bulk GRN details: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PurchaseEntryBulkApproveView(APIView):
    """
    Bulk GRN Approval API

    Purpose:
        Approve or reject multiple GRNs at once.
        Useful for batch processing of pending GRNs.

    Endpoint:
        POST /api/pharmacy/purchase-entries/bulk-approve/

    Request Body:
        {
            "grn_ids": [123, 124, 125],
            "action": "approve",  // or "reject"
            "rejection_reason": "Optional reason for rejection"
        }

    Response:
        {
            "status": "success",
            "approved_count": 2,
            "rejected_count": 0,
            "failed_count": 1,
            "results": [
                {
                    "grn_id": 123,
                    "grn_number": "GRN-20251216-0001",
                    "status": "success",
                    "new_status": "APPROVED",
                    "stock_entries_verified": 5
                },
                {
                    "grn_id": 124,
                    "grn_number": "GRN-20251216-0002",
                    "status": "failed",
                    "error": "Cannot process GRN with status: Approved"
                }
            ]
        }
    """

    @transaction.atomic
    def post(self, request):
        """
        Approve or reject multiple GRNs

        Request Body:
            {
                "grn_ids": [123, 124, 125],
                "action": "approve" or "reject",
                "rejection_reason": "Optional reason if rejecting"
            }

        Returns:
            200: Bulk approval results
            400: Validation error
        """
        try:
            # Validate request
            grn_ids = request.data.get('grn_ids', [])
            action = request.data.get('action', '').lower()
            rejection_reason = request.data.get('rejection_reason', '')

            if not grn_ids:
                return Response({
                    'status': 'error',
                    'message': 'grn_ids is required and must be a non-empty list'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not isinstance(grn_ids, list):
                return Response({
                    'status': 'error',
                    'message': 'grn_ids must be a list of integers'
                }, status=status.HTTP_400_BAD_REQUEST)

            if action not in ['approve', 'reject']:
                return Response({
                    'status': 'error',
                    'message': 'action must be either "approve" or "reject"'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate all IDs are integers
            try:
                grn_ids = [int(id) for id in grn_ids]
            except (ValueError, TypeError):
                return Response({
                    'status': 'error',
                    'message': 'All grn_ids must be valid integers'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Limit to prevent abuse
            if len(grn_ids) > 50:
                return Response({
                    'status': 'error',
                    'message': 'Maximum 50 GRNs can be processed at once'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Fetch GRNs
            grns = PurchaseEntry.objects.prefetch_related('stock_entries').filter(id__in=grn_ids)

            # Track results
            results = []
            approved_count = 0
            rejected_count = 0
            failed_count = 0

            # Process each GRN
            for grn in grns:
                try:
                    # Check if GRN can be approved/rejected
                    if grn.status != 'PENDING':
                        results.append({
                            'grn_id': grn.id,
                            'grn_number': grn.grn_number,
                            'status': 'failed',
                            'error': f'Cannot process GRN with status: {grn.get_status_display()}'
                        })
                        failed_count += 1
                        continue

                    if action == 'approve':
                        # Approve GRN
                        grn.status = 'APPROVED'
                        grn.approved_by = request.user
                        grn.approved_date = timezone.now()
                        grn.stock_created = True
                        grn.save()

                        # Mark all related stock entries as verified
                        stock_entries = grn.stock_entries.all()
                        verified_count = 0
                        for stock in stock_entries:
                            stock.is_verified = True
                            stock.verified_by = request.user
                            stock.verified_date = timezone.now()
                            stock.save()
                            verified_count += 1

                        results.append({
                            'grn_id': grn.id,
                            'grn_number': grn.grn_number,
                            'status': 'success',
                            'new_status': 'APPROVED',
                            'stock_entries_verified': verified_count
                        })
                        approved_count += 1

                        logger.info(f"Bulk approval - GRN approved: {grn.grn_number} by {request.user.username}, {verified_count} stock entries verified")

                    elif action == 'reject':
                        # Reject GRN
                        grn.status = 'REJECTED'
                        grn.approved_by = request.user
                        grn.approved_date = timezone.now()
                        if rejection_reason:
                            grn.notes = f"REJECTED: {rejection_reason}\n\n{grn.notes or ''}"
                        grn.save()

                        # Mark all related stock entries as inactive
                        stock_entries = grn.stock_entries.all()
                        inactive_count = 0
                        for stock in stock_entries:
                            stock.is_active = False
                            stock.save()
                            inactive_count += 1

                        results.append({
                            'grn_id': grn.id,
                            'grn_number': grn.grn_number,
                            'status': 'success',
                            'new_status': 'REJECTED',
                            'stock_entries_deactivated': inactive_count,
                            'rejection_reason': rejection_reason
                        })
                        rejected_count += 1

                        logger.info(f"Bulk approval - GRN rejected: {grn.grn_number} by {request.user.username}")

                except Exception as e:
                    results.append({
                        'grn_id': grn.id,
                        'grn_number': grn.grn_number,
                        'status': 'failed',
                        'error': str(e)
                    })
                    failed_count += 1
                    logger.error(f"Error processing GRN {grn.grn_number} in bulk approval: {str(e)}")

            # Check for GRNs that were not found
            found_ids = [grn.id for grn in grns]
            not_found_ids = [id for id in grn_ids if id not in found_ids]

            for not_found_id in not_found_ids:
                results.append({
                    'grn_id': not_found_id,
                    'grn_number': None,
                    'status': 'failed',
                    'error': 'GRN not found'
                })
                failed_count += 1

            logger.info(f"Bulk GRN approval completed by {request.user.username}: {approved_count} approved, {rejected_count} rejected, {failed_count} failed")

            return Response({
                'status': 'success',
                'message': f'Bulk {action} completed',
                'approved_count': approved_count,
                'rejected_count': rejected_count,
                'failed_count': failed_count,
                'total_processed': len(grn_ids),
                'results': results
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in bulk GRN approval: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Failed to process bulk approval: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PurchaseEntryApproveView(APIView):
    """
    GRN Approval API - Pharmacist Verification

    Purpose:
        Allow pharmacist to approve/verify GRN entries.
        Upon approval, all related stock entries are marked as verified and become available for dispensing.

    Endpoint:
        POST /api/pharmacy/purchase-entries/<grn_id>/approve/
        POST /api/pharmacy/purchase-entries/<grn_id>/reject/

    Workflow:
        1. Pharmacist reviews GRN details
        2. Pharmacist approves or rejects
        3. If approved: Stock marked as verified (is_verified=True)
        4. If rejected: GRN status set to REJECTED, stock remains unverified

    Features:
        - Verify GRN details before stock becomes active
        - Prevent incorrect stock entries from being dispensed
        - Track who approved and when
        - Handle rejection with reason
    """

    @transaction.atomic
    def post(self, request, grn_id):
        """
        POST: Approve or Reject a GRN

        Request Body:
            {
                "action": "approve" or "reject",
                "rejection_reason": "Optional reason if rejecting"
            }

        Returns:
            200: GRN approved/rejected successfully
            404: GRN not found
            400: Invalid status for approval
        """
        try:
            # Get GRN
            try:
                grn = PurchaseEntry.objects.prefetch_related('stock_entries').get(id=grn_id)
            except PurchaseEntry.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'Purchase entry (GRN) not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Check if GRN can be approved/rejected
            if grn.status != 'PENDING':
                return Response({
                    'status': 'error',
                    'message': f'Cannot process GRN with status: {grn.get_status_display()}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get action
            action = request.data.get('action', '').lower()

            if action == 'approve':
                # Approve GRN
                grn.status = 'APPROVED'
                grn.approved_by = request.user
                grn.approved_date = timezone.now()
                grn.stock_created = True
                grn.save()

                # Mark all related stock entries as verified
                stock_entries = grn.stock_entries.all()
                verified_count = 0
                for stock in stock_entries:
                    stock.is_verified = True
                    stock.verified_by = request.user
                    stock.verified_date = timezone.now()
                    stock.save()
                    verified_count += 1

                logger.info(f"GRN approved: {grn.grn_number} by {request.user.username}, {verified_count} stock entries verified")

                return Response({
                    'status': 'success',
                    'message': 'GRN approved successfully. Stock is now available for dispensing.',
                    'data': {
                        'grn_number': grn.grn_number,
                        'status': grn.status,
                        'approved_by': request.user.username,
                        'approved_date': grn.approved_date,
                        'stock_entries_verified': verified_count
                    }
                }, status=status.HTTP_200_OK)

            elif action == 'reject':
                # Reject GRN
                rejection_reason = request.data.get('rejection_reason', '')

                grn.status = 'REJECTED'
                grn.approved_by = request.user
                grn.approved_date = timezone.now()
                if rejection_reason:
                    grn.notes = f"REJECTED: {rejection_reason}\n\n{grn.notes or ''}"
                grn.save()

                # Mark all related stock entries as inactive
                stock_entries = grn.stock_entries.all()
                for stock in stock_entries:
                    stock.is_active = False
                    stock.save()

                logger.info(f"GRN rejected: {grn.grn_number} by {request.user.username}")

                return Response({
                    'status': 'success',
                    'message': 'GRN rejected. Stock entries marked as inactive.',
                    'data': {
                        'grn_number': grn.grn_number,
                        'status': grn.status,
                        'rejected_by': request.user.username,
                        'rejection_reason': rejection_reason
                    }
                }, status=status.HTTP_200_OK)

            else:
                return Response({
                    'status': 'error',
                    'message': 'Invalid action. Use "approve" or "reject"'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error processing GRN approval: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PurchaseEntryItemsView(APIView):
    """
    Get GRN Items API

    Endpoint:
        GET /api/pharmacy/purchase-entries/<id>/items/

    Features:
        - Get all items in a GRN
        - Show stock entry details
        - Display medication information
    """

    def get(self, request, grn_id):
        """
        Get all items in a GRN

        Returns:
            200: List of items with details
            404: GRN not found
        """
        try:
            try:
                grn = PurchaseEntry.objects.get(id=grn_id)
            except PurchaseEntry.DoesNotExist:
                return Response({
                    'error': 'Purchase entry not found'
                }, status=status.HTTP_404_NOT_FOUND)

            items = grn.purchase_items.select_related('medication', 'stock_entry').all()

            return Response({
                'grn_number': grn.grn_number,
                'items_count': items.count(),
                'items': PurchaseItemSerializer(items, many=True).data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching GRN items: {str(e)}")
            return Response({
                'error': 'Failed to fetch GRN items',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# SUPPLIER RETURN (PURCHASE RETURN) MANAGEMENT APIs
# ============================================================================

class SupplierReturnView(APIView):
    """
    Supplier Return Management API

    Endpoints:
        POST /api/pharmacy/supplier-returns/ - Create new return
        GET /api/pharmacy/supplier-returns/ - List all returns with filtering
        GET /api/pharmacy/supplier-returns/<id>/ - Get return details
        PATCH /api/pharmacy/supplier-returns/<id>/ - Update return
        DELETE /api/pharmacy/supplier-returns/<id>/ - Delete/Deactivate return

    Features:
        - Create returns to supplier with nested items
        - Auto-calculate totals and GST
        - Auto-adjust stock when return is created
        - Link to original GRN (optional)
        - Track credit notes from supplier
        - Filter by supplier, status, reason, date range
        - Pagination support
    """

    @transaction.atomic
    def post(self, request):
        """
        Create a new supplier return

        Request Body:
            {
                "supplier": 1,
                "purchase_entry": 1,  // optional
                "return_date": "2025-12-02",
                "reason": "DAMAGED",
                "status": "PENDING",
                "notes": "Items damaged in transit",
                "items": [
                    {
                        "medication": 1,
                        "stock_entry": 5,
                        "batch_number": "BATCH-001",
                        "expiry_date": "2026-12-31",
                        "quantity_returned": 50,
                        "unit_price": 6.00,
                        "cgst_percent": 6.00,
                        "sgst_percent": 6.00,
                        "condition": "DAMAGED",
                        "reason_detail": "Packaging damaged"
                    }
                ]
            }

        Returns:
            201: Return created successfully
            400: Validation error
        """
        try:
            # Add created_by
            data = request.data.copy()

            serializer = SupplierReturnCreateSerializer(data=data)

            if serializer.is_valid():
                # Save with created_by
                supplier_return = serializer.save(created_by=request.user)

                logger.info(f"Supplier Return created: {supplier_return.return_number} by {request.user.username}")

                return Response({
                    'message': 'Supplier return created successfully',
                    'data': SupplierReturnSerializer(supplier_return).data
                }, status=status.HTTP_201_CREATED)

            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error creating supplier return: {str(e)}")
            return Response({
                'error': 'Failed to create supplier return',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, return_id=None):
        """
        Get supplier return details or list returns

        Query Parameters (for list):
            - supplier_id: Filter by supplier
            - purchase_entry_id: Filter by GRN
            - status: Filter by status
            - reason: Filter by reason
            - return_date_from: From date
            - return_date_to: To date
            - search: Search by return number
            - page: Page number (default: 1)
            - page_size: Items per page (default: 20)

        Returns:
            200: Return details or list
            404: Return not found
        """
        try:
            # Get single return by ID
            if return_id:
                try:
                    supplier_return = SupplierReturn.objects.select_related(
                        'supplier', 'purchase_entry'
                    ).prefetch_related('return_items__medication').get(id=return_id)

                    return Response({
                        'data': SupplierReturnSerializer(supplier_return).data
                    }, status=status.HTTP_200_OK)
                except SupplierReturn.DoesNotExist:
                    return Response({
                        'error': 'Supplier return not found'
                    }, status=status.HTTP_404_NOT_FOUND)

            # List returns with filtering
            queryset = SupplierReturn.objects.select_related(
                'supplier', 'purchase_entry'
            ).all().order_by('-return_date', '-created_on')

            # Filter by supplier
            supplier_id = request.GET.get('supplier_id')
            if supplier_id:
                queryset = queryset.filter(supplier_id=supplier_id)

            # Filter by GRN
            purchase_entry_id = request.GET.get('purchase_entry_id')
            if purchase_entry_id:
                queryset = queryset.filter(purchase_entry_id=purchase_entry_id)

            # Filter by status
            status_filter = request.GET.get('status')
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            # Filter by reason
            reason = request.GET.get('reason')
            if reason:
                queryset = queryset.filter(reason=reason)

            # Filter by date range
            return_date_from = request.GET.get('return_date_from')
            if return_date_from:
                queryset = queryset.filter(return_date__gte=return_date_from)

            return_date_to = request.GET.get('return_date_to')
            if return_date_to:
                queryset = queryset.filter(return_date__lte=return_date_to)

            # Search by return number
            search = request.GET.get('search')
            if search:
                queryset = queryset.filter(return_number__icontains=search)

            # Filter by active status
            is_active = request.GET.get('is_active')
            if is_active is not None:
                is_active_bool = is_active.lower() == 'true'
                queryset = queryset.filter(is_active=is_active_bool)

            # Pagination
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)

            total_count = queryset.count()
            start = (page - 1) * page_size
            end = start + page_size

            returns = queryset[start:end]

            return Response({
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size,
                'data': SupplierReturnListSerializer(returns, many=True).data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching supplier returns: {str(e)}")
            return Response({
                'error': 'Failed to fetch supplier returns',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, return_id):
        """
        Update supplier return

        Can update: status, credit_note details, dates
        Cannot update: items after creation

        Request Body (partial update):
            {
                "status": "APPROVED",
                "credit_note_number": "CN-2025-001",
                "credit_note_date": "2025-12-05",
                "credit_note_amount": 3500.00
            }

        Returns:
            200: Return updated successfully
            404: Return not found
            400: Validation error
        """
        try:
            try:
                supplier_return = SupplierReturn.objects.get(id=return_id)
            except SupplierReturn.DoesNotExist:
                return Response({
                    'error': 'Supplier return not found'
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = SupplierReturnSerializer(
                supplier_return, data=request.data, partial=True
            )

            if serializer.is_valid():
                # Save with updated_by
                supplier_return = serializer.save(
                    updated_by=request.user,
                    updated_on=timezone.now()
                )

                # If status changed to APPROVED, update approved fields
                if 'status' in request.data and request.data['status'] == 'APPROVED':
                    supplier_return.approved_by = request.user
                    supplier_return.approved_date = timezone.now()
                    supplier_return.save()

                logger.info(f"Supplier Return updated: {supplier_return.return_number} by {request.user.username}")

                return Response({
                    'message': 'Supplier return updated successfully',
                    'data': SupplierReturnSerializer(supplier_return).data
                }, status=status.HTTP_200_OK)

            return Response({
                'error': 'Validation error',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error updating supplier return: {str(e)}")
            return Response({
                'error': 'Failed to update supplier return',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, return_id):
        """
        Delete/Deactivate supplier return (soft delete)

        Note: Stock adjustment is NOT reversed automatically.
        Admin should manually adjust stock if needed.

        Returns:
            200: Return deactivated successfully
            404: Return not found
        """
        try:
            try:
                supplier_return = SupplierReturn.objects.get(id=return_id)
            except SupplierReturn.DoesNotExist:
                return Response({
                    'error': 'Supplier return not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Soft delete
            supplier_return.is_active = False
            supplier_return.status = 'CANCELLED'
            supplier_return.updated_by = request.user
            supplier_return.updated_on = timezone.now()
            supplier_return.save()

            logger.info(f"Supplier Return cancelled: {supplier_return.return_number} by {request.user.username}")

            return Response({
                'message': 'Supplier return cancelled successfully',
                'return_number': supplier_return.return_number
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error deleting supplier return: {str(e)}")
            return Response({
                'error': 'Failed to delete supplier return',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SupplierReturnApproveView(APIView):
    """
    Approve Supplier Return API

    Endpoint:
        POST /api/pharmacy/supplier-returns/<id>/approve/

    Features:
        - Change status to APPROVED
        - Record who approved and when
        - Log approval action
    """

    def post(self, request, return_id):
        """
        Approve a supplier return

        Returns:
            200: Return approved successfully
            404: Return not found
            400: Invalid status for approval
        """
        try:
            try:
                supplier_return = SupplierReturn.objects.get(id=return_id)
            except SupplierReturn.DoesNotExist:
                return Response({
                    'error': 'Supplier return not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Check if return can be approved
            if supplier_return.status in ['COMPLETED', 'CANCELLED', 'REJECTED']:
                return Response({
                    'error': f'Cannot approve return with status {supplier_return.status}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if already adjusted (prevent double adjustment)
            if supplier_return.status == 'PENDING':
                # Approve return
                supplier_return.status = 'APPROVED'
                supplier_return.approved_by = request.user
                supplier_return.approved_date = timezone.now()
                supplier_return.updated_by = request.user
                supplier_return.updated_on = timezone.now()
                supplier_return.save()

                # Adjust stock NOW (on approval)
                supplier_return.adjust_stock()

                logger.info(f"Supplier Return approved and stock adjusted: {supplier_return.return_number} by {request.user.username}")

                return Response({
                    'message': 'Supplier return approved successfully and stock adjusted',
                    'return_number': supplier_return.return_number,
                    'status': supplier_return.status
                }, status=status.HTTP_200_OK)
            else:
                # Already approved, just return success
                return Response({
                    'message': 'Return already approved',
                    'return_number': supplier_return.return_number,
                    'status': supplier_return.status
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error approving supplier return: {str(e)}")
            return Response({
                'error': 'Failed to approve supplier return',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SupplierReturnItemsView(APIView):
    """
    Get Supplier Return Items API

    Endpoint:
        GET /api/pharmacy/supplier-returns/<id>/items/

    Features:
        - Get all items in a return
        - Show stock entry details
        - Display medication information
    """

    def get(self, request, return_id):
        """
        Get all items in a supplier return

        Returns:
            200: List of items with details
            404: Return not found
        """
        try:
            try:
                supplier_return = SupplierReturn.objects.get(id=return_id)
            except SupplierReturn.DoesNotExist:
                return Response({
                    'error': 'Supplier return not found'
                }, status=status.HTTP_404_NOT_FOUND)

            items = supplier_return.return_items.select_related(
                'medication', 'stock_entry', 'purchase_item'
            ).all()

            return Response({
                'return_number': supplier_return.return_number,
                'items_count': items.count(),
                'items': SupplierReturnItemSerializer(items, many=True).data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching supplier return items: {str(e)}")
            return Response({
                'error': 'Failed to fetch supplier return items',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# SECTION 1: PHARMACIST PROFILE MANAGEMENT
# ============================================================================
# Purpose: Create and manage pharmacist staff profiles
# Related Models: PharmacistStaff, User, Group
# ============================================================================


class PharmacistProfileView(APIView):
    """
    Pharmacist Profile Creation API

    Purpose:
        Creates a new pharmacist user account with associated profile.
        Automatically assigns user to pharmacist group (Group ID: 5).
        Sends login credentials via email upon successful creation.

    Methods:
        POST: Create new pharmacist profile

    Request Body:
        username (str): Unique username for login
        email (str): Email address (used for credential delivery)
        password (str): Initial password
        first_name (str): First name
        last_name (str): Last name
        date_of_birth (date): Birth date
        gender (str): Gender (MALE/FEMALE/OTHER)
        contact_number (str): Primary contact
        employee_id (str): Unique employee identifier
        hire_date (date): Employment start date
        shift_schedule (str): Work shift details
        profile_picture (file, optional): Profile photo

    Response:
        201: Pharmacist created successfully
        400: Validation error or duplicate username/email
        500: Server error

    Related Models:
        - User: Django auth user
        - PharmacistStaff: Pharmacist profile details
        - Group: User group assignment
    """

    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request):
        """Create pharmacist user and profile"""

        # Extract required fields
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')

        # Validate required fields
        if not username or not email or not password:
            return Response({
                "detail": "Username, email and password are required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check for existing username
        if User.objects.filter(username=username).exists():
            return Response({
                "detail": "Username already exists"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check for existing email
        if User.objects.filter(email=email).exists():
            return Response({
                "detail": "Email already exists"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create Django user account
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Assign to pharmacist group (ID: 5)
            front_desk_group = Group.objects.get(id=5)
            user.groups.add(front_desk_group)
            user.save()

        except Group.DoesNotExist:
            user.delete()
            return Response({
                "detail": "Pharmacist group with ID 5 does not exist"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "detail": f"Failed to create user: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Prepare pharmacist profile data
        front_desk_data = {
            'user': user.id,
            'date_of_birth': request.data.get('date_of_birth'),
            'gender': request.data.get('gender'),
            'hire_date': request.data.get('hire_date'),
            'contact_number': request.data.get('contact_number'),
            'email': email,
            'employee_id': request.data.get('employee_id'),
            'shift_schedule': request.data.get('shift_schedule'),
        }

        # Add profile picture if provided
        if 'profile_picture' in request.FILES:
            front_desk_data['profile_picture'] = request.FILES['profile_picture']

        # Create pharmacist profile
        serializer = PharmacistSerializer(data=front_desk_data)
        if serializer.is_valid():
            pharmacist = serializer.save()

            try:
                # Send credentials email
                send_doctor_credentials_email(
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    username=username,
                    password=password
                )
                response_data = {
                    "message": "Pharmacist profile created successfully. Credentials have been sent to their email."
                }

            except Exception as e:
                # If email fails, return credentials in response
                response_data = {
                    "message": "Pharmacist profile created successfully, but failed to send email with credentials.",
                    "warning": "Please provide the pharmacist with their credentials manually.",
                    "credentials": {
                        "username": username,
                        "password": password
                    }
                }
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            user.delete()
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# SECTION 2: MEDICATION & STOCK MANAGEMENT
# ============================================================================
# Purpose: Manage medication catalog and inventory (OPD Pharmacy)
# Related Models: Medication, MedicationStock, MedicationDispense
# Business Logic: Batch tracking, FIFO dispensing, expiry management
# ============================================================================


class MedicationView(APIView):
    """
    Medication Master Data Management API

    Purpose:
        Manages the medication catalog (drug master list).
        Each medication can have multiple stock batches.

    Methods:
        POST: Create new medication entry
        GET: List all medications created by current user

    POST Request Body:
        name (str): Medication name
        description (str, optional): Medication details
        dosage_form (str): Form (Tablet, Capsule, Syrup, Injection)
        strength (str): Strength (e.g., '500mg', '10ml')

    GET Response:
        Returns list of active medications with basic details

    Related Models:
        - Medication: Drug master data
        - MedicationStock: Stock batches linked to medication

    Business Rules:
        - Medications are user-specific (created_by filter)
        - Only active medications are returned
        - Soft delete supported (is_active flag)
    """

    # permission_classes = [IsAdminUser]

    def post(self, request):
        """Create new medication in catalog"""
        try:
            serializer = MedicationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(created_by=request.user)
            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "Medication created successfully"
            }, status=status.HTTP_201_CREATED)

        except serializers.ValidationError as e:
            # Handle validation errors (including duplicate medication)
            logger.warning(f"Medication validation failed: {str(e)}")
            error_detail = e.detail

            # Extract the error message
            if isinstance(error_detail, dict) and 'detail' in error_detail:
                message = error_detail['detail']
            elif isinstance(error_detail, dict):
                # Flatten the error dict to a readable message
                message = "; ".join([f"{k}: {v[0] if isinstance(v, list) else v}"
                                   for k, v in error_detail.items()])
            else:
                message = str(error_detail)

            return Response({
                "status": "error",
                "message": message,
                "errors": error_detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Medication creation failed: {str(e)}")
            return Response({
                "status": "error",
                "message": "Failed to create medication. Please try again."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        """List all active medications created by current user"""
        try:
            medications = Medication.objects.filter(
                is_active=True
            )
            serializer = MedicationSerializer(medications, many=True)
            return Response({
                "status": "success",
                "data": serializer.data
            })
        except Exception as e:
            logger.error(f"Failed to fetch medications: {str(e)}")
            return Response({
                "status": "error",
                "message": "Failed to fetch medications"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MedicationStockView(APIView):
    """
    Medication Stock Management API

    Purpose:
        Manages medication inventory with batch-wise tracking.
        Supports adding new stock, updating quantities, and viewing available stock.

    Methods:
        POST: Add new stock batch
        PATCH: Update existing stock batch
        GET: List all stock entries with availability

    POST Request Body:
        medication (int): Medication ID
        batch_number (str): Batch number from manufacturer
        quantity (int): Current quantity in stock
        opening_quantity (int, optional): Opening stock (default: 0)
        received_quantity (int, optional): Total received (default: 0)
        sold_quantity (int, optional): Total sold (default: 0)
        returned_quantity (int, optional): Returned to supplier (default: 0)
        damaged_quantity (int, optional): Damaged/written off (default: 0)
        adjusted_quantity (int, optional): Stock adjustments +/- (default: 0)
        expiry_date (date): Expiry date
        received_date (date): Date received
        purchase_price (decimal): Procurement cost per unit
        selling_price (decimal): Retail price per unit
        mrp (decimal, optional): Maximum Retail Price
        supplier (str): Supplier name
        manufacturer (str): Manufacturer name

    PATCH Request Body:
        stock_id (int): Stock entry ID to update
        (any fields to update)

    GET Response:
        Returns list of stock entries with:
        - Medication details
        - Current quantity (quantity field)
        - Opening/received/sold/returned/damaged/adjusted quantities
        - Available quantity (after dispensing)
        - Batch information
        - Pricing (purchase_price, selling_price, mrp)
        - Expiry status flags (is_expired, is_near_expiry, is_low_stock, is_out_of_stock)
        - Computed fields (expiration_status, days_to_expiry, current_stock)

    Related Models:
        - MedicationStock: Stock batch records
        - Medication: Linked drug details
        - MedicationDispense: Dispensing transactions

    Business Logic:
        - Auto-calculates expiry status on save
        - Auto-sets is_out_of_stock flag when quantity = 0
        - Expired stock shows 0 available quantity
        - FIFO logic applied during dispensing
    """

    # permission_classes = [IsPharmacist]

    def post(self, request):
        """Add new medication stock batch"""
        try:
            with transaction.atomic():
                serializer = MedicationStockSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                stock = serializer.save(created_by=request.user)

                return Response({
                    "status": "success",
                    "batch_id": stock.id,
                    "data": MedicationStockSerializer(stock).data
                }, status=status.HTTP_201_CREATED)

        except serializers.ValidationError as e:
            return Response({
                "status": "error",
                "message": e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except IntegrityError as e:
            logger.error(f"Stock creation integrity error: {str(e)}")
            return Response({
                "status": "error",
                "message": f"Database integrity error: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Stock creation failed: {str(e)}")
            return Response({
                "status": "error",
                "message": f"Stock creation failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def patch(self, request):
        """Update existing stock batch (partial update)"""
        try:
            with transaction.atomic():
                stock_id = request.data.get("stock_id")
                if not stock_id:
                    return Response({
                        "status": "error",
                        "message": "Missing required field: stock_id"
                    }, status=status.HTTP_400_BAD_REQUEST)

                try:
                    stock = MedicationStock.objects.get(id=stock_id)
                except MedicationStock.DoesNotExist:
                    return Response({
                        "status": "error",
                        "message": "Stock batch not found"
                    }, status=status.HTTP_404_NOT_FOUND)

                # Partial update with patch
                serializer = MedicationStockSerializer(
                    stock,
                    data=request.data,
                    partial=True
                )
                serializer.is_valid(raise_exception=True)

                # Save with audit trail - set updated_by and updated_on
                updated_stock = serializer.save(
                    updated_by=request.user,
                    updated_on=timezone.now()
                )

                return Response({
                    "status": "success",
                    "message": "Stock updated successfully",
                    "data": MedicationStockSerializer(updated_stock).data
                }, status=status.HTTP_200_OK)

        except serializers.ValidationError as e:
            return Response({
                "status": "error",
                "message": e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def get(self, request):
        """
        List all stock entries with calculated availability

        Logic:
            1. Fetch all stock entries for active medications (user-specific)
            2. Check expiry date against today
            3. Calculate available quantity = original - dispensed
            4. Return formatted data with medication details
        """
        india_tz = pytz.timezone('Asia/Kolkata')
        today = datetime.now(india_tz).date()

        stock_entries = MedicationStock.objects.select_related(
            'medication'
        ).filter(
            medication__is_active=True,
        )

        result_data = []

        try:
            for stock in stock_entries:
                # If expired, set available to 0
                if stock.expiry_date <= today:
                    available = 0
                else:
                    # Calculate dispensed quantity from MedicationDispense records
                    dispensed = MedicationDispense.objects.filter(
                        stock_entry=stock
                    ).aggregate(
                        Sum('quantity_dispensed')
                    )['quantity_dispensed__sum'] or 0

                    available = max(0, stock.quantity - dispensed)

                result_data.append({
                    "stock_id": stock.id,
                    "medication": stock.medication.id,
                    "medicine_name": stock.medication.name,
                    "dosage_form": stock.medication.dosage_form,
                    "strength": stock.medication.strength,
                    "manufacturer": stock.manufacturer,
                    "available_quantity": available,
                    "added_quantity": stock.quantity,
                    "selling_price": str(stock.selling_price),
                    "purchase_price": str(stock.purchase_price),
                    "batch_number": stock.batch_number or None,
                    "received_date": stock.received_date,
                    "expiry_date": stock.expiry_date.strftime("%Y-%m-%d"),
                    "supplier": stock.supplier,
                    "is_active": stock.is_active,
                    # Department allocation fields
                    "pharmacy_quantity": stock.pharmacy_quantity,
                    "home_care_quantity": stock.home_care_quantity,
                    "casualty_quantity": stock.casualty_quantity,
                    "unallocated_quantity": stock.get_unallocated_quantity(),
                    "allocated_total": stock.get_allocated_total()
                })

            return Response({
                "status": "success",
                "count": len(result_data),
                "data": result_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Stock listing error: {str(e)}")
            return Response({
                "status": "error",
                "message": "Failed to fetch stock data"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DispenseView(APIView):
    """
    Generic Medication Dispensing API (FIFO Logic)

    Purpose:
        Dispenses medication using First-In-First-Out (FIFO) logic.
        Automatically selects batches by expiry date (earliest first).
        NOT USED in current workflow (replaced by PrescribedMedicationDispense).

    Methods:
        POST: Dispense medication quantity

    Request Body:
        medication_id (int): Medication to dispense
        quantity (int): Quantity to dispense

    Response:
        200: Dispensed successfully with batch breakdown
        400: Insufficient stock or validation error
        500: Server error

    Business Logic:
        1. Fetch all non-expired batches ordered by expiry_date (FIFO)
        2. Lock batches using select_for_update() for thread safety
        3. Check total availability
        4. Deduct from earliest expiry batches first
        5. Continue until quantity fulfilled

    Related Models:
        - MedicationStock: Stock batches
        - Medication: Drug details

    Note: This is a standalone dispense API not linked to prescriptions.
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        """Dispense medication using FIFO (First-In-First-Out) logic"""
        serializer = DispenseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "status": "error",
                "message": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                medication = get_object_or_404(
                    Medication,
                    pk=serializer.validated_data['medication_id']
                )
                quantity = serializer.validated_data['quantity']

                # Get batches ordered by expiry (FIFO) with row-level lock
                batches = MedicationStock.objects.filter(
                    medication=medication,
                    quantity__gt=0,
                    expiry_date__gt=timezone.now().date()
                ).select_for_update().order_by('expiry_date')

                # Check total availability
                total_available = batches.aggregate(
                    Sum('quantity')
                )['quantity__sum'] or 0

                if total_available < quantity:
                    return Response({
                        "status": "error",
                        "message": f"Only {total_available} units available"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Dispense from batches using FIFO
                dispensed = []
                remaining = quantity

                for batch in batches:
                    if remaining <= 0:
                        break

                    # Deduct from current batch and update sold quantity
                    deduct = min(batch.quantity, remaining)
                    batch.quantity = F('quantity') - deduct
                    batch.sold_quantity = F('sold_quantity') + deduct
                    batch.save(update_fields=['quantity', 'sold_quantity'])

                    dispensed.append({
                        "batch": batch.batch_number,
                        "deducted": deduct,
                        "remaining": batch.quantity - deduct
                    })
                    remaining -= deduct

                return Response({
                    "status": "success",
                    "dispensed_from": dispensed,
                    "total_dispensed": quantity
                })

        except Exception as e:
            logger.error(f"Dispense error: {str(e)}")
            return Response({
                "status": "error",
                "message": "Dispensing failed"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# SECTION 3: DOCTOR CONSULTATION & PRESCRIPTION MANAGEMENT
# ============================================================================
# Purpose: Manage doctor consultations and prescribed medications
# Related Models: DoctorConsultation, PrescribedMedicine, Appointment
# Workflow: Consultation → Prescription → Dispensing → Billing
# ============================================================================


class DoctorConsultationView(APIView):
    """
    Doctor Consultation Management API

    Purpose:
        Creates and retrieves doctor consultation records with prescriptions.
        Supports follow-up appointment linking.

    Methods:
        GET: Retrieve consultation(s) by ID, appointment, or patient
        POST: Create new consultation with prescribed medicines
        PUT: Update existing consultation

    GET Query Parameters:
        consultation_id (int): Get specific consultation
        appointment_id (int): Get consultations for appointment
        patient_id (str): Get patient's consultation history

    POST Request Body:
        appointment_id (int): Associated appointment
        diagnosis (str): Doctor's diagnosis
        recommended_tests (list, optional): Lab tests to perform
        doctor_notes (str, optional): Additional notes
        follow_up_date (date, optional): Follow-up date
        prescribed_medicines (list, optional): List of prescriptions
            - medicine_id (int): Medication ID
            - dosage (str): Dosage instruction
            - frequency (str): Frequency (e.g., "Twice daily")
            - duration (str): Duration (e.g., "7 days")
            - quantity (int): Total quantity to dispense
            - instructions (str, optional): Special instructions

    Response:
        GET: Consultation details with prescribed medicines
        POST: Created consultation with follow-up appointment (if applicable)
        PUT: Updated consultation confirmation

    Related Models:
        - DoctorConsultation: Consultation record
        - PrescribedMedicine: Prescription details
        - Appointment: Associated appointment
        - Medication: Prescribed drugs

    Business Logic:
        - Prevents duplicate consultations (same appointment + diagnosis)
        - Auto-creates follow-up appointment if follow_up_date provided
        - Updates appointment status to PRESCRIPTION_READY or DISPENSED
        - No stock validation during prescription (done at dispensing)
    """

    def get(self, request):
        """
        Retrieve consultation(s) based on query parameters

        Supports three query modes:
        1. consultation_id: Get single consultation
        2. appointment_id: Get consultation(s) for appointment
        3. patient_id: Get patient's full consultation history
        """
        try:
            consultation_id = request.query_params.get('consultation_id')
            appointment_id = request.query_params.get('appointment_id')
            patient_id = request.query_params.get('patient_id')

            if not any([consultation_id, appointment_id, patient_id]):
                return Response({
                    "status": "error",
                    "message": "At least one query parameter is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Mode 1: Get single consultation by ID
            if consultation_id:
                try:
                    consultation = DoctorConsultation.objects.select_related(
                        'appointment__patient',
                        'appointment__doctor'
                    ).prefetch_related(
                        'prescribedmedicine_set__medicine'
                    ).get(id=consultation_id)

                    return Response({
                        "status": "success",
                        "data": self._format_consultation_response(consultation)
                    }, status=status.HTTP_200_OK)

                except DoctorConsultation.DoesNotExist:
                    return Response({
                        "status": "error",
                        "message": f"Consultation not found"
                    }, status=status.HTTP_404_NOT_FOUND)

            # Mode 2: Get consultation(s) by appointment ID
            elif appointment_id:
                consultations = DoctorConsultation.objects.select_related(
                    'appointment__patient',
                    'appointment__doctor'
                ).prefetch_related(
                    'prescribedmedicine_set__medicine'
                ).filter(appointment_id=appointment_id)

                if not consultations.exists():
                    return Response({
                        "status": "error",
                        "message": f"No consultations found"
                    }, status=status.HTTP_404_NOT_FOUND)

                return Response({
                    "status": "success",
                    "count": consultations.count(),
                    "data": [self._format_consultation_response(c) for c in consultations]
                }, status=status.HTTP_200_OK)

            # Mode 3: Get consultation history by patient ID
            elif patient_id:
                consultations = DoctorConsultation.objects.select_related(
                    'appointment__patient',
                    'appointment__doctor'
                ).prefetch_related(
                    'prescribedmedicine_set__medicine'
                ).filter(
                    appointment__patient_id=patient_id
                ).order_by('-created_at')

                if not consultations.exists():
                    return Response({
                        "status": "error",
                        "message": f"No consultations found"
                    }, status=status.HTTP_404_NOT_FOUND)

                return Response({
                    "status": "success",
                    "count": consultations.count(),
                    "data": [self._format_consultation_response(c) for c in consultations]
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _format_consultation_response(self, consultation):
        """Helper method to format consultation data for response"""

        # Get follow-up appointment if exists
        follow_up_appointment = None
        follow_up_appointments = Appointment.objects.filter(
            parent_consultation=consultation
        )
        if follow_up_appointments.exists():
            follow_up_appointment = follow_up_appointments.first()

        # Format prescribed medicines
        prescribed_medicines = []
        for pm in consultation.prescribedmedicine_set.all():
            prescribed_medicines.append({
                "id": pm.id,
                "medicine_id": pm.medicine.id,
                "medicine_name": pm.medicine.name,
                "medicine_dosage_form": pm.medicine.dosage_form,
                "medicine_strength": pm.medicine.strength,
                "dosage": pm.dosage,
                "frequency": pm.frequency,
                "duration": pm.duration,
                "quantity": pm.quantity,
                "instructions": pm.instructions
            })

        return {
            "id": consultation.id,
            "appointment_id": consultation.appointment.id,
            "appointment_date": consultation.appointment.appointment_date,
            "patient_id": consultation.appointment.patient.id,
            "patient_name": f"{consultation.appointment.patient.first_name} {consultation.appointment.patient.last_name}",
            "doctor_id": consultation.appointment.doctor.id,
            "doctor_name": f"{consultation.appointment.doctor.user.first_name} {consultation.appointment.doctor.user.last_name}",
            "diagnosis": consultation.diagnosis,
            "recommended_tests": consultation.recommended_tests,
            "doctor_notes": consultation.doctor_notes,
            "follow_up_date": consultation.follow_up_date,
            "follow_up_appointment_id": follow_up_appointment.id if follow_up_appointment else None,
            "follow_up_linked": follow_up_appointment is not None,
            "prescribed_medicines": prescribed_medicines,
        }

    def post(self, request):
        """
        Create new consultation with prescribed medicines and lab tests

        Workflow:
        1. Validate appointment exists
        2. Check for duplicate consultation
        3. Create consultation record
        4. Create lab test order if recommended_tests provided
        5. Create prescribed medicine records (no stock validation)
        6. Handle follow-up appointment creation/linking
        7. Update appointment status
        """
        try:
            with transaction.atomic():
                data = request.data

                # Validate required fields
                if not data.get('appointment_id'):
                    return Response({
                        "status": "error",
                        "message": "appointment_id is required"
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not data.get('diagnosis'):
                    return Response({
                        "status": "error",
                        "message": "diagnosis is required"
                    }, status=status.HTTP_400_BAD_REQUEST)

                medicines_data = data.get('prescribed_medicines', [])

                # Get appointment
                appointment_id = data.get('appointment_id')
                try:
                    appointment = Appointment.objects.get(id=appointment_id)
                except Appointment.DoesNotExist:
                    return Response({
                        "status": "error",
                        "message": f"Appointment with ID {appointment_id} not found"
                    }, status=status.HTTP_404_NOT_FOUND)

                # Check for duplicate consultation
                duplicate_consultation = DoctorConsultation.objects.filter(
                    appointment=appointment_id,
                    diagnosis=data.get('diagnosis')
                ).exists()

                if duplicate_consultation:
                    return Response({
                        "status": "error",
                        "message": "A consultation with the same diagnosis already exists for this appointment"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Process follow_up_date if provided
                follow_up_date = None
                if data.get('follow_up_date'):
                    try:
                        follow_up_date = datetime.strptime(
                            data.get('follow_up_date'),
                            '%Y-%m-%d'
                        ).date()
                    except ValueError:
                        return Response({
                            "status": "error",
                            "message": "follow_up_date must be in YYYY-MM-DD format"
                        }, status=status.HTTP_400_BAD_REQUEST)

                # Create consultation
                consultation = DoctorConsultation.objects.create(
                    appointment=appointment,
                    diagnosis=data.get('diagnosis'),
                    recommended_tests=data.get('recommended_tests', []),
                    doctor_notes=data.get('doctor_notes', ''),
                    follow_up_date=follow_up_date
                )

                # Process recommended lab tests if provided
                lab_order = None
                recommended_tests_data = data.get('recommended_tests', [])
                if recommended_tests_data and isinstance(recommended_tests_data, list) and len(recommended_tests_data) > 0:
                    # Calculate total amount from test rates
                    total_amount = Decimal('0.00')
                    for test in recommended_tests_data:
                        rate = test.get('rate', 0)
                        total_amount += Decimal(str(rate))

                    # Generate order number
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    order_number = f"LAB-{timestamp}"

                    # Create lab test order
                    lab_order = LabTestOrder.objects.create(
                        patient=appointment.patient,
                        appointment=appointment,
                        order_number=order_number,
                        selected_tests=recommended_tests_data,  # Store the full test array
                        external_lab_name="To be assigned",  # Can be updated later
                        status='ORDERED',
                        total_amount=total_amount,
                        paid_amount=Decimal('0.00'),
                        discount=Decimal('0.00'),  # Explicitly set as Decimal to avoid float error
                        payment_status='UNPAID',
                        date_ordered=timezone.now().date(),
                        created_by=request.user if hasattr(request, 'user') else None
                    )

                    # Link lab departments (ManyToMany)
                    lab_department_ids = [test.get('id') for test in recommended_tests_data if test.get('id')]
                    if lab_department_ids:
                        lab_order.lab_departments.set(lab_department_ids)

                # Process prescribed medicines if provided
                prescribed_medicines = []
                if medicines_data:
                    for med_data in medicines_data:
                        # Validate medicine data
                        if not med_data.get('medicine_id'):
                            return Response({
                                "status": "error",
                                "message": "medicine_id is required for each prescribed medicine"
                            }, status=status.HTTP_400_BAD_REQUEST)

                        if not med_data.get('quantity'):
                            return Response({
                                "status": "error",
                                "message": "quantity is required for each prescribed medicine"
                            }, status=status.HTTP_400_BAD_REQUEST)

                        medicine_id = med_data.get('medicine_id')
                        quantity = int(med_data.get('quantity'))

                        # Validate medicine exists
                        try:
                            medicine = Medication.objects.get(id=medicine_id)
                        except Medication.DoesNotExist:
                            return Response({
                                "status": "error",
                                "message": f"Medicine with ID {medicine_id} not found"
                            }, status=status.HTTP_404_NOT_FOUND)

                        # Create prescribed medicine (no stock validation)
                        prescribed_medicine = PrescribedMedicine.objects.create(
                            consultation=consultation,
                            medicine=medicine,
                            dosage=med_data.get('dosage', ''),
                            frequency=med_data.get('frequency', ''),
                            duration=med_data.get('duration', ''),
                            quantity=quantity,
                            instructions=med_data.get('instructions', '')
                        )
                        prescribed_medicines.append(prescribed_medicine)

                # Handle follow-up appointment creation/linking
                follow_up_appointment_id = None
                if follow_up_date:
                    # Look for existing appointment on follow_up_date
                    existing_follow_up = Appointment.objects.filter(
                        patient=appointment.patient,
                        doctor=appointment.doctor,
                        appointment_date=follow_up_date,
                        is_follow_up=False
                    ).first()

                    if existing_follow_up:
                        # Link existing appointment
                        existing_follow_up.parent_consultation = consultation
                        existing_follow_up.is_follow_up = True
                        existing_follow_up.save()
                        follow_up_appointment_id = existing_follow_up.id
                    else:
                        # Create new follow-up appointment
                        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                        follow_up_appointment_id_str = f"APT-{timestamp}-FU"

                        follow_up_appointment = Appointment.objects.create(
                            appointment_id=follow_up_appointment_id_str,
                            patient=appointment.patient,
                            doctor=appointment.doctor,
                            appointment_date=follow_up_date,
                            appointment_time=appointment.appointment_time,
                            visit_reason=f"Follow-up for: {data.get('diagnosis', 'Previous consultation')}",
                            visit_status='FOLLOW_UP',
                            parent_consultation=consultation,
                            is_follow_up=True,
                            created_by=request.user
                        )
                        follow_up_appointment_id = follow_up_appointment.id

                # Prepare response data
                response_data = {
                    "id": consultation.id,
                    "appointment_id": appointment.id,
                    "patient_name": appointment.patient.first_name,
                    "appointment_date": appointment.appointment_date,
                    "diagnosis": consultation.diagnosis,
                    "recommended_tests": consultation.recommended_tests,
                    "doctor_notes": consultation.doctor_notes,
                    "follow_up_date": consultation.follow_up_date,
                    "follow_up_appointment_id": follow_up_appointment_id,
                    "follow_up_linked": follow_up_appointment_id is not None,
                    "prescribed_medicines": [],
                    "lab_order": None,
                    "message": "Follow-up appointment created successfully" if follow_up_date and follow_up_appointment_id else "Consultation created successfully"
                }

                # Add lab order details to response if created
                if lab_order:
                    response_data["lab_order"] = {
                        "id": lab_order.id,
                        "order_number": lab_order.order_number,
                        "total_amount": str(lab_order.total_amount),
                        "payment_status": lab_order.payment_status,
                        "status": lab_order.status,
                        "selected_tests": lab_order.selected_tests
                    }

                # Add prescribed medicines to response
                for pm in prescribed_medicines:
                    response_data["prescribed_medicines"].append({
                        "id": pm.id,
                        "medicine_id": pm.medicine.id,
                        "medicine_name": pm.medicine.name,
                        "medicine_dosage_form": pm.medicine.dosage_form,
                        "medicine_strength": pm.medicine.strength,
                        "dosage": pm.dosage,
                        "frequency": pm.frequency,
                        "duration": pm.duration,
                        "quantity": pm.quantity,
                        "instructions": pm.instructions
                    })

                # Update appointment status
                appointment_status = Appointment.objects.get(id=appointment_id)
                if medicines_data:
                    appointment_status.visit_status = 'PRESCRIPTION_READY'
                else:
                    appointment_status.visit_status = 'DISPENSED'
                appointment_status.save()

                # Return success response
                return Response({
                    "status": "success",
                    "message": "Consultation created successfully",
                    "data": response_data
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        """Update existing consultation (full or partial update)"""
        try:
            consultation_id = request.data.get('consultation_id')

            if not consultation_id:
                return Response({
                    "status": "error",
                    "message": "consultation_id is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            consultation = DoctorConsultation.objects.get(id=consultation_id)

            # Update fields
            consultation.diagnosis = request.data.get('diagnosis', consultation.diagnosis)
            consultation.doctor_notes = request.data.get('doctor_notes', consultation.doctor_notes)
            consultation.recommended_tests = request.data.get('recommended_tests', consultation.recommended_tests)
            consultation.follow_up_date = request.data.get('follow_up_date', consultation.follow_up_date)
            consultation.save()

            # Handle medicines update if provided
            if 'prescribed_medicines' in request.data:
                # Delete existing prescriptions
                PrescribedMedicine.objects.filter(consultation=consultation).delete()

                # Create new prescriptions
                for medicine_data in request.data['prescribed_medicines']:
                    PrescribedMedicine.objects.create(
                        consultation=consultation,
                        medicine_id=medicine_data['medicine_id'],
                        dosage=medicine_data.get('dosage', ''),
                        frequency=medicine_data.get('frequency', ''),
                        duration=medicine_data.get('duration', ''),
                        quantity=medicine_data.get('quantity', 1),
                        instructions=medicine_data.get('instructions', '')
                    )

            return Response({
                "status": "success",
                "message": "Consultation updated successfully"
            }, status=status.HTTP_200_OK)

        except DoctorConsultation.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Consultation not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientHistoryView(APIView):
    """
    Patient Consultation History API

    Purpose:
        Retrieves complete consultation history for a patient.
        Includes prescribed medicines, follow-up tracking, and parent consultation links.

    Methods:
        GET: Get patient's consultation history

    URL Parameters:
        patient_id (str): Patient ID to fetch history

    Response:
        200: Patient info + consultation history
        404: No appointments or consultations found
        500: Server error

    Response Structure:
        - patient_info: Demographics and contact details
        - total_consultations: Count of consultations
        - consultation_history: List of consultations with:
            - Consultation details
            - Prescribed medicines
            - Follow-up information
            - Parent consultation (if this is a follow-up)

    Related Models:
        - PatientRegistration: Patient details
        - Appointment: Patient appointments
        - DoctorConsultation: Consultation records
        - PrescribedMedicine: Prescriptions
    """

    def get(self, request, patient_id):
        """Get complete consultation history for a patient"""
        try:
            # Get all appointments for the patient
            patient_appointments = Appointment.objects.filter(
                patient__patient_id=patient_id
            )

            if not patient_appointments.exists():
                return Response({
                    "status": "error",
                    "message": f"No appointments found for patient ID {patient_id}"
                }, status=status.HTTP_404_NOT_FOUND)

            # Get all consultations with optimized queries
            consultations = DoctorConsultation.objects.filter(
                appointment__in=patient_appointments
            ).select_related(
                'appointment',
                'appointment__patient',
                'appointment__doctor',
                'appointment__doctor__user',
                'appointment__doctor__specialization',
                'appointment__parent_consultation'
            ).prefetch_related(
                'prescribed_medicines',
                'prescribedmedicine_set__medicine'
            ).order_by('-created_on')

            if not consultations.exists():
                return Response({
                    "status": "success",
                    "message": "No consultation history found for this patient",
                    "data": {
                        "patient_info": {
                            "patient_id": patient_appointments.first().patient.patient_id,
                            "name": f"{patient_appointments.first().patient.first_name} {patient_appointments.first().patient.last_name}",
                            "age": patient_appointments.first().patient.age,
                            "gender": patient_appointments.first().patient.get_gender_display()
                        },
                        "consultation_history": []
                    }
                }, status=status.HTTP_200_OK)

            # Format consultation history
            history_data = []
            for consultation in consultations:
                # Get prescribed medicines
                prescribed_medicines = []
                for prescribed in consultation.prescribedmedicine_set.all():
                    prescribed_medicines.append({
                        "medicine_name": prescribed.medicine.name,
                        "dosage": prescribed.dosage,
                        "frequency": prescribed.frequency,
                        "duration": prescribed.duration,
                        "quantity": prescribed.quantity,
                        "instructions": prescribed.instructions
                    })

                # Check for follow-ups
                follow_up_appointments = consultation.follow_up_appointments.all()
                has_follow_ups = follow_up_appointments.exists()

                # Check if this is a follow-up
                is_follow_up = consultation.appointment.is_follow_up
                parent_consultation_info = None
                if is_follow_up and consultation.appointment.parent_consultation:
                    parent_consultation_info = {
                        "parent_consultation_id": consultation.appointment.parent_consultation.id,
                        "parent_appointment_date": consultation.appointment.parent_consultation.appointment.appointment_date,
                        "parent_diagnosis": consultation.appointment.parent_consultation.diagnosis
                    }

                history_data.append({
                    "consultation_id": consultation.id,
                    "appointment_date": consultation.appointment.appointment_date,
                    "doctor_name": f"Dr. {consultation.appointment.doctor.user.first_name} {consultation.appointment.doctor.user.last_name}",
                    "department": consultation.appointment.doctor.specialization.name if consultation.appointment.doctor.specialization else None,
                    "diagnosis": consultation.diagnosis,
                    "doctor_notes": consultation.doctor_notes,
                    "recommended_tests": consultation.recommended_tests,
                    "follow_up_date": consultation.follow_up_date,
                    "prescribed_medicines": prescribed_medicines,
                    "consultation_date": consultation.created_on.date(),
                    "is_follow_up": is_follow_up,
                    "parent_consultation": parent_consultation_info,
                    "has_scheduled_follow_ups": has_follow_ups,
                    "follow_up_count": follow_up_appointments.count() if has_follow_ups else 0
                })

            # Get patient info
            patient = patient_appointments.first().patient

            return Response({
                "status": "success",
                "message": "Patient history retrieved successfully",
                "data": {
                    "patient_info": {
                        "patient_id": patient.patient_id,
                        "name": f"{patient.first_name} {patient.last_name}",
                        "age": patient.age,
                        "gender": patient.get_gender_display(),
                        "contact_number": patient.contact_number,
                        "email": patient.email,
                        "allergies": patient.allergies,
                        "registration_date": patient.registration_date
                    },
                    "total_consultations": consultations.count(),
                    "consultation_history": history_data
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# SECTION 4: PHARMACY QUEUE & PRESCRIPTION DISPENSING
# ============================================================================
# Purpose: Pharmacy workflow - view prescription queue and dispense medicines
# Related Models: Appointment, DoctorConsultation, PrescribedMedicine
# Workflow: Prescription Ready → At Pharmacy → Dispensed → Billing
# ============================================================================


class PharmaConsultationView(APIView):
    """
    Pharmacy Queue API

    Purpose:
        Lists patients waiting at pharmacy for medication dispensing.
        Filters by appointment date and visit status.

    Methods:
        GET: List pharmacy queue

    Query Parameters:
        filter_type (str): 'today', 'week', 'month', 'date_range'
        start_date (date): Start date for 'date_range' filter
        end_date (date): End date for 'date_range' filter

    Response:
        Returns list of patients with:
        - Patient details
        - Consultation ID
        - Appointment details
        - Visit status
        - is_view flag (true if already dispensed)

    Visit Statuses Included:
        - PRESCRIPTION_READY: Waiting for dispensing
        - AT_PHARMACY: Currently being served
        - DISPENSED: Already dispensed (view mode)
        - AT_BILLING: At billing counter
        - PAYMENT_COMPLETE: Payment done

    Related Models:
        - Appointment: Appointment details
        - DoctorConsultation: Linked consultation
        - PatientRegistration: Patient details
    """

    # permission_classes = [IsPharmacist]

    def get(self, request):
        """List patients in pharmacy queue with date filtering"""
        try:
            filter_type = request.query_params.get('filter_type', 'today')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')

            india_tz = pytz.timezone('Asia/Kolkata')
            today = datetime.now(india_tz).date()

            # Apply date filter based on filter_type
            if filter_type == 'today':
                date_filter = {'appointment_date': today}
            elif filter_type == 'week':
                week_start = today - timedelta(days=today.weekday())
                week_end = week_start + timedelta(days=6)
                date_filter = {'appointment_date__range': (week_start, week_end)}
            elif filter_type == 'month':
                month_start = today.replace(day=1)
                next_month = month_start + timedelta(days=32)
                month_end = next_month.replace(day=1) - timedelta(days=1)
                date_filter = {'appointment_date__range': (month_start, month_end)}
            elif filter_type == 'date_range':
                if not start_date or not end_date:
                    return Response({
                        'status': 'error',
                        'message': 'start_date and end_date are required for date_range filter'
                    }, status=status.HTTP_400_BAD_REQUEST)
                date_filter = {'appointment_date__range': (start_date, end_date)}
            else:
                return Response({
                    'status': 'error',
                    'message': 'Invalid filter_type. Use: today, week, month, or date_range'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get appointments in pharmacy workflow
            appointments = Appointment.objects.filter(
                visit_status__in=[
                    'PRESCRIPTION_READY',
                    'AT_PHARMACY',
                    'DISPENSED',
                    'AT_BILLING',
                    'PAYMENT_COMPLETE'
                ],
                **date_filter
            )

            data = []
            for appointment in appointments:
                # is_view = True means already dispensed (view-only mode)
                is_view = appointment.visit_status in [
                    'DISPENSED',
                    'AT_BILLING',
                    'PAYMENT_COMPLETE'
                ]

                consultation = DoctorConsultation.objects.get(
                    appointment=appointment
                )

                data.append({
                    "consultation_id": consultation.id,
                    "appointment_id": appointment.appointment_id,
                    "patient_name": f"{appointment.patient.first_name} {appointment.patient.last_name}",
                    "patient_phone": appointment.patient.contact_number,
                    "patient_id": appointment.patient.patient_id,
                    "appointment_date": appointment.appointment_date,
                    "appointment_time": appointment.appointment_time,
                    "visit_status": appointment.visit_status,
                    "doctor_name": f"Dr. {appointment.doctor.user.first_name}",
                    "is_view": is_view
                })

            return Response({
                "count": len(data),
                "status": "success",
                "pharmacy_queue": data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PharmaPrescribedMedicineView(APIView):
    """
    Prescription Details with Stock Availability API

    Purpose:
        Retrieves consultation details with prescribed medicines.
        Shows available stock batches and calculates pricing.

    Methods:
        POST: Get prescription details with pricing

    Request Body:
        consultation_id (int): Consultation ID

    Response:
        Returns:
        - Consultation details
        - Prescribed medicines with:
            - Medicine details
            - Available stock batches
            - Unit price and total price
        - Total prescription amount

    Business Logic:
        - Fetches all prescribed medicines for consultation
        - For each medicine, gets available stock batches (quantity > 0)
        - Uses first available stock's price for calculation
        - Calculates total_price = unit_price * quantity

    Related Models:
        - DoctorConsultation: Consultation details
        - PrescribedMedicine: Prescriptions
        - MedicationStock: Available stock batches
        - Medication: Medicine details
    """

    def post(self, request):
        """Get consultation prescription details with pricing"""
        try:
            consultation_id = request.data.get('consultation_id')
            if not consultation_id:
                return Response({
                    "status": "error",
                    "message": "consultation_id is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                consultation = DoctorConsultation.objects.get(id=consultation_id)
            except DoctorConsultation.DoesNotExist:
                return Response({
                    "status": "error",
                    "message": "Consultation not found"
                }, status=status.HTTP_404_NOT_FOUND)

            # Get prescribed medicines
            prescribed_medicines = PrescribedMedicine.objects.filter(
                consultation=consultation
            ).select_related('medicine')

            response_data = {
                "consultation_id": consultation.id,
                "appointment_id": consultation.appointment.id,
                "patient_name": f"{consultation.appointment.patient.first_name} {consultation.appointment.patient.last_name}",
                "patient_id": consultation.appointment.patient.patient_id,
                "appointment_date": consultation.appointment.appointment_date,
                "diagnosis": consultation.diagnosis,
                "recommended_tests": consultation.recommended_tests,
                "doctor_notes": consultation.doctor_notes,
                "follow_up_date": consultation.follow_up_date,
                "prescribed_medicines": [],
                "total_prescription_amount": "0.00",
                "doctor_name": f"{consultation.appointment.doctor.user.first_name} {consultation.appointment.doctor.user.last_name}"
            }

            total_amount = Decimal('0.00')

            # Process each prescribed medicine
            for pm in prescribed_medicines:
                # Get available stock entries (exclude expired batches, order by FIFO)
                from django.utils import timezone
                today = timezone.now().date()

                available_stocks = MedicationStock.objects.filter(
                    medication=pm.medicine,
                    quantity__gt=0,
                    expiry_date__gt=today,  # Exclude expired batches
                    is_active=True  # Only active stock entries
                ).order_by('expiry_date')  # FIFO: Earliest expiry first

                # Calculate pricing
                unit_price = None
                total_price = Decimal('0.00')
                stock_list = []

                # Build stock list with recommendation and expiry details
                remaining_qty = pm.quantity
                for idx, stock in enumerate(available_stocks):
                    # First stock(s) that can fulfill the quantity are recommended (FIFO)
                    is_recommended = False
                    if remaining_qty > 0:
                        is_recommended = True
                        if stock.quantity >= remaining_qty:
                            remaining_qty = 0
                        else:
                            remaining_qty -= stock.quantity

                    # Calculate days to expiry
                    days_to_expiry = (stock.expiry_date - today).days

                    # Determine expiry warning level
                    expiry_warning = None
                    if days_to_expiry <= 30:
                        expiry_warning = "CRITICAL"  # Expires within 30 days
                    elif days_to_expiry <= 90:
                        expiry_warning = "WARNING"   # Expires within 90 days
                    elif days_to_expiry <= 180:
                        expiry_warning = "NOTICE"    # Expires within 6 months

                    stock_data = {
                        'id': stock.id,
                        'batch_number': stock.batch_number,
                        'expiry_date': stock.expiry_date,
                        'days_to_expiry': days_to_expiry,
                        'expiry_warning': expiry_warning,
                        'quantity': stock.quantity,
                        'selling_price': str(stock.selling_price),
                        'recommended': is_recommended  # FIFO recommendation flag - UI can highlight these
                    }
                    stock_list.append(stock_data)  # Return ALL stocks with recommendation flag

                if stock_list:
                    # Use first available stock price (FIFO - first recommended batch)
                    unit_price = Decimal(stock_list[0]['selling_price'])
                    total_price = unit_price * pm.quantity

                medicine_data = {
                    "prescription_id": pm.id,
                    "medicine_id": pm.medicine.id,
                    "medicine_name": pm.medicine.name,
                    "medicine_dosage_form": pm.medicine.dosage_form,
                    "medicine_strength": pm.medicine.strength,
                    "dosage": pm.dosage,
                    "frequency": pm.frequency,
                    "duration": pm.duration,
                    "quantity": pm.quantity,
                    "instructions": pm.instructions,
                    "available_stocks": stock_list,
                    "unit_price": str(unit_price) if unit_price else None,
                    "total_price": str(total_price)
                }

                response_data["prescribed_medicines"].append(medicine_data)
                total_amount += total_price

            response_data["total_prescription_amount"] = str(total_amount)

            return Response({
                "status": "success",
                "data": response_data
            })

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PrescribedMedicationDispense(APIView):
    """
    Prescription-Based Medication Dispensing API (Bulk)

    Purpose:
        Dispenses prescribed medications from selected stock batches.
        Supports bulk dispensing for entire prescription.
        Validates stock availability and prescription limits.

    Methods:
        POST: Dispense prescribed medicines

    Request Body (List of dispense items):
        [
            {
                "prescribed_medicine_id": int,
                "stock_entry_id": int,
                "quantity_dispensed": int
            },
            ...
        ]

    Response:
        201: Dispensing successful
        400: Validation error or insufficient stock
        404: Stock/prescription not found
        500: Server error

    Validations:
        1. All required fields present
        2. No duplicate prescription/stock combinations
        3. Stock availability check
        4. Prescription limit check (can't dispense more than prescribed)

    Business Logic:
        1. Lock stock entries using select_for_update()
        2. Aggregate quantities by stock and prescription
        3. Validate stock availability
        4. Validate prescription limits
        5. Create MedicationDispense records (bulk)
        6. Stock quantity NOT updated here (done elsewhere)
        7. Update appointment status to DISPENSED

    Related Models:
        - PrescribedMedicine: Prescription details
        - MedicationStock: Stock batches
        - MedicationDispense: Dispensing records
        - Appointment: Update status
    """

    permission_classes = [IsPharmacist]

    def post(self, request):
        """Bulk dispense prescribed medications"""
        data = request.data

        # Get appointment ID from first prescription
        prescribed_medicine_id = data[0]['prescribed_medicine_id']
        prescribed_medicine = PrescribedMedicine.objects.get(
            id=prescribed_medicine_id
        )
        appointment_id = prescribed_medicine.consultation.appointment.id

        # Validate request is a list
        if not isinstance(data, list):
            return Response({
                "status": "error",
                "message": "Expected a list of dispense items"
            }, status=status.HTTP_400_BAD_REQUEST)

        required_fields = ['prescribed_medicine_id', 'stock_entry_id', 'quantity_dispensed']
        seen_combinations = set()

        # Validate each dispense item
        for index, item in enumerate(data):
            # Check required fields
            if not all(field in item for field in required_fields):
                return Response({
                    "status": "error",
                    "message": f"Item {index} missing required fields"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate quantity
            try:
                item['quantity_dispensed'] = int(item['quantity_dispensed'])
                if item['quantity_dispensed'] <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                return Response({
                    "status": "error",
                    "message": f"Invalid quantity in item {index}"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check for duplicates
            combo = (item['prescribed_medicine_id'], item['stock_entry_id'])
            if combo in seen_combinations:
                return Response({
                    "status": "error",
                    "message": f"Duplicate prescription/stock combination in item {index}"
                }, status=status.HTTP_400_BAD_REQUEST)
            seen_combinations.add(combo)

        try:
            with transaction.atomic():
                # Lock stock entries and prescriptions
                stock_ids = [item['stock_entry_id'] for item in data]
                pm_ids = [item['prescribed_medicine_id'] for item in data]

                stocks = MedicationStock.objects.filter(
                    id__in=stock_ids
                ).select_for_update()
                stocks_dict = {stock.id: stock for stock in stocks}

                prescribed_meds = PrescribedMedicine.objects.filter(
                    id__in=pm_ids
                ).select_for_update()
                prescribed_meds_dict = {pm.id: pm for pm in prescribed_meds}

                # Validate all IDs exist
                for index, item in enumerate(data):
                    stock_id = item['stock_entry_id']
                    pm_id = item['prescribed_medicine_id']

                    if stock_id not in stocks_dict:
                        return Response({
                            "status": "error",
                            "message": f"Stock {stock_id} not found in item {index}"
                        }, status=status.HTTP_404_NOT_FOUND)

                    if pm_id not in prescribed_meds_dict:
                        return Response({
                            "status": "error",
                            "message": f"Prescription {pm_id} not found in item {index}"
                        }, status=status.HTTP_404_NOT_FOUND)

                # Aggregate quantities
                stock_totals = defaultdict(int)
                prescription_totals = defaultdict(int)

                for item in data:
                    stock_id = item['stock_entry_id']
                    pm_id = item['prescribed_medicine_id']
                    qty = item['quantity_dispensed']

                    stock_totals[stock_id] += qty
                    prescription_totals[pm_id] += qty

                # Check stock availability
                warnings = []
                for stock_id, total in stock_totals.items():
                    stock = stocks_dict[stock_id]
                    if stock.quantity < total:
                        warnings.append({
                            "medicine": stock.medication.name,
                            "available": stock.quantity,
                            "required": total,
                            "warning": f"Insufficient stock for {stock.medication.name}. Available: {stock.quantity}, Required: {total}"
                        })

                # Check prescription limits
                for pm_id, total in prescription_totals.items():
                    pm = prescribed_meds_dict[pm_id]
                    dispensed_total = MedicationDispense.objects.filter(
                        prescribed_medicine=pm
                    ).aggregate(
                        Sum('quantity_dispensed')
                    )['quantity_dispensed__sum'] or 0

                    if dispensed_total + total > pm.quantity:
                        return Response({
                            "status": "error",
                            "message": f"Prescription limit exceeded for {pm.medicine.name}. Prescribed: {pm.quantity}, Dispensed: {dispensed_total + total}"
                        }, status=status.HTTP_400_BAD_REQUEST)

                # Create dispense records
                dispenses = []
                for item in data:
                    dispenses.append(MedicationDispense(
                        prescribed_medicine=prescribed_meds_dict[item['prescribed_medicine_id']],
                        stock_entry=stocks_dict[item['stock_entry_id']],
                        quantity_dispensed=item['quantity_dispensed'],
                        dispensed_by=request.user
                    ))

                # Bulk create dispense records
                MedicationDispense.objects.bulk_create(dispenses)

                # Update appointment status
                appointment = Appointment.objects.get(id=appointment_id)
                appointment.visit_status = 'DISPENSED'
                appointment.save()

                response_data = {
                    "status": "success",
                    "message": f"Dispensed {len(dispenses)} items successfully",
                    "dispensed_items": len(dispenses)
                }

                # Add warnings if any
                if warnings:
                    response_data["warnings"] = warnings
                    response_data["message"] = f"Dispensed {len(dispenses)} items successfully with warnings"

                return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# SECTION 5: PATIENT BILLING & PAYMENT
# ============================================================================
# Purpose: Generate and manage patient bills (consultation + medicines)
# Related Models: PatientBill, Appointment, DoctorConsultation
# Workflow: Dispensed → Bill Preview → Save Bill → Payment Complete
# ============================================================================


class FinalBillPreviewView(APIView):
    """
    Final Bill Preview API (Consultation + Medicines)

    Purpose:
        Generates bill preview showing consultation fee and dispensed medicines.
        Only includes medicines that have been actually dispensed.

    Methods:
        POST: Generate bill preview

    Request Body:
        consultation_id (int): Consultation ID

    Response:
        Returns bill preview with:
        - Patient details
        - Dispensed medicines (only actually dispensed)
        - Consultation fee
        - Total medicine cost
        - Total bill amount
        - Bill number (next available)
        - Amount in words

    Business Logic:
        1. Get consultation and prescribed medicines
        2. For each prescription, check MedicationDispense records
        3. Only include medicines that have dispenses
        4. Calculate totals from actual dispensed quantities
        5. Add consultation fee
        6. Generate bill number preview

    Related Models:
        - DoctorConsultation: Consultation details
        - PrescribedMedicine: Prescriptions
        - MedicationDispense: Actual dispensing records
        - Doctor: For consultation fee
    """

    # permission_classes = [IsAdminUser]

    def post(self, request):
        """Generate bill preview showing only dispensed medicines"""
        try:
            consultation_id = request.data.get('consultation_id')
            consultation = DoctorConsultation.objects.get(id=consultation_id)

            medicine_items = []
            total_medicine_cost = 0
            errors = []

            # Get all prescribed medicines
            prescribed_medicines = PrescribedMedicine.objects.filter(
                consultation=consultation
            )

            # Process only dispensed medicines
            for prescribed in prescribed_medicines:
                try:
                    # Check if any dispenses exist
                    dispenses = MedicationDispense.objects.filter(
                        prescribed_medicine=prescribed
                    )

                    if not dispenses.exists():
                        continue  # Skip if not dispensed

                    # Calculate totals from dispenses
                    total_dispensed = sum(d.quantity_dispensed for d in dispenses)
                    subtotal = sum(
                        d.stock_entry.selling_price * d.quantity_dispensed
                        for d in dispenses
                    )

                    medicine = prescribed.medicine

                    medicine_items.append({
                        'medicine_name': f"{medicine.name} {medicine.strength}",
                        'unit_price': dispenses.first().stock_entry.selling_price,
                        'dispensed_quantity': total_dispensed,
                        'subtotal': subtotal
                    })

                    total_medicine_cost += subtotal

                except Exception as e:
                    errors.append(f"Error processing {prescribed.medicine.name}: {str(e)}")
                    continue

            if errors:
                return Response({
                    "errors": errors
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Calculate totals
            consultation_fee = consultation.appointment.doctor.doctor_consultation_fee
            total_amount = consultation_fee + total_medicine_cost
            total_bill_words = num_to_words(total_amount)

            bill_data = {
                'patient': f"{consultation.appointment.patient.first_name} {consultation.appointment.patient.last_name}",
                'dispensed_medicines': medicine_items,
                'total_medicine_cost': total_medicine_cost,
                'consultation_fee': consultation_fee,
                'total_amount': total_amount,
                'total_amount_words': total_bill_words,
                'consultation_id': consultation.id,
                'doctor_name': f"{consultation.appointment.doctor.user.first_name} {consultation.appointment.doctor.user.last_name}",
                'patient_id': consultation.appointment.patient.patient_id,
                'department': consultation.appointment.doctor.specialization.department.name,
                'bill_no': get_next_bill_id(consultation.appointment.id),
                'appointment_date': consultation.appointment.appointment_date,
                'appointment_time': consultation.appointment.appointment_time,
                'app_f_id': consultation.appointment.id
            }

            return Response(bill_data, status=status.HTTP_200_OK)

        except DoctorConsultation.DoesNotExist:
            return Response({
                "error": "Consultation not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BillingConsultationView(APIView):
    """
    Billing Queue API

    Purpose:
        Lists patients waiting at billing counter.
        Shows only dispensed patients ready for billing.

    Endpoint:
        GET /api/pharmacy/billing-queue/ - Get billing queue with date filtering

    Query Parameters:
        - filter_type: 'today', 'week', 'month', 'custom' (default: 'today')
        - from_date: Start date for custom range (YYYY-MM-DD)
        - to_date: End date for custom range (YYYY-MM-DD)
        - visit_status: Filter by visit status (default: 'DISPENSED')

    Methods:
        GET: List billing queue

    Response:
        Returns list of patients with:
        - Consultation details
        - Patient information
        - Appointment details
        - Visit status

    Features:
        - Filter appointments by date ranges
        - Filter by visit status
        - Query optimization with select_related
        - Ordered by appointment date and time

    Related Models:
        - Appointment: Appointment details
        - DoctorConsultation: Consultation link
        - PatientRegistration: Patient details
    """

    # permission_classes = [IsReceptionist]

    def get(self, request):
        """List patients in billing queue with date filtering

        Query Parameters:
        - filter_type: 'today', 'week', 'month', 'custom' (default: 'today')
        - from_date: Start date for custom range (YYYY-MM-DD)
        - to_date: End date for custom range (YYYY-MM-DD)
        - visit_status: Filter by visit status (default: 'DISPENSED')
        """
        try:
            india_tz = pytz.timezone('Asia/Kolkata')
            today = datetime.now(india_tz).date()

            # Get filter parameters
            filter_type = request.query_params.get('filter_type', 'today').lower()
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')
            visit_status_param = request.query_params.get('visit_status', 'DISPENSED')

            # Calculate date range based on filter_type
            if filter_type == 'today':
                start_date = today
                end_date = today
            elif filter_type == 'week':
                start_date = today - timedelta(days=today.weekday())  # Monday of current week
                end_date = start_date + timedelta(days=6)  # Sunday
            elif filter_type == 'month':
                start_date = today.replace(day=1)  # First day of current month
                next_month = start_date.replace(day=28) + timedelta(days=4)
                end_date = next_month - timedelta(days=next_month.day)  # Last day of current month
            elif filter_type == 'custom':
                if not from_date or not to_date:
                    return Response({
                        "status": "error",
                        "message": "from_date and to_date are required for custom filter"
                    }, status=status.HTTP_400_BAD_REQUEST)

                try:
                    start_date = datetime.strptime(from_date, '%Y-%m-%d').date()
                    end_date = datetime.strptime(to_date, '%Y-%m-%d').date()

                    if start_date > end_date:
                        return Response({
                            "status": "error",
                            "message": "from_date cannot be after to_date"
                        }, status=status.HTTP_400_BAD_REQUEST)
                except ValueError:
                    return Response({
                        "status": "error",
                        "message": "Invalid date format. Use YYYY-MM-DD"
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    "status": "error",
                    "message": "Invalid filter_type. Use 'today', 'week', 'month', or 'custom'"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Filter appointments by date range and visit status
            appointments = Appointment.objects.filter(
                visit_status=visit_status_param,
                appointment_date__gte=start_date,
                appointment_date__lte=end_date
            ).select_related(
                'patient', 'doctor', 'doctor__user'
            ).order_by('appointment_date', 'appointment_time')

            if not appointments:
                return Response({
                    "status": "success",
                    "message": f"No appointments found for the selected date range",
                    "count": 0,
                    "pharmacy_queue": []
                }, status=status.HTTP_200_OK)

            data = []
            for appointment in appointments:
                try:
                    consultation = DoctorConsultation.objects.get(
                        appointment=appointment
                    )

                    data.append({
                        "consultation_id": consultation.id,
                        "appointment_id": appointment.id,
                        "patient_name": f"{appointment.patient.first_name} {appointment.patient.last_name}",
                        "patient_phone": appointment.patient.contact_number,
                        "patient_id": appointment.patient.patient_id,
                        "appointment_date": appointment.appointment_date,
                        "appointment_time": appointment.appointment_time,
                        "visit_status": appointment.visit_status,
                        "doctor_name": f"Dr. {appointment.doctor.user.first_name}{appointment.doctor.user.last_name}",
                    })
                except DoctorConsultation.DoesNotExist:
                    continue

            return Response({
                "count": len(data),
                "status": "success",
                "pharmacy_queue": data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Generated_bill_save(APIView):
    """
    Save Patient Bill API

    Purpose:
        Saves final patient bill to database.
        Prevents duplicate bill creation.
        Updates appointment status to PAYMENT_COMPLETE.

    Methods:
        POST: Save bill

    Request Body:
        (Uses Bill_Serializer fields)
        appointment (int): Appointment ID
        consultation (int): Consultation ID
        (other bill fields)

    Response:
        201: Bill saved successfully
        200: Bill already exists (duplicate prevention)
        400: Validation error
        500: Server error

    Business Logic:
        1. Check if bill already exists for appointment
        2. If exists, return success (idempotent)
        3. If not, create new bill using serializer
        4. Update appointment status to PAYMENT_COMPLETE

    Related Models:
        - PatientBill: Bill record
        - Appointment: Update status
    """

    # permission_classes = [IsReceptionist]

    def post(self, request):
        """Save patient bill (with duplicate check)"""
        try:
            data = request.data
            appointment_id = data['appointment']

            # Check for existing bill
            try:
                PatientBill.objects.get(appointment=appointment_id)
                return Response({
                    "status": "success",
                    "message": "Bill already exists"
                }, status=status.HTTP_200_OK)
            except PatientBill.DoesNotExist:
                pass

            # Create new bill
            bill_serializer = Bill_Serializer(data=data)
            if bill_serializer.is_valid():
                bill_serializer.save(created_by=request.user)

                # Update appointment status
                appointment = Appointment.objects.get(id=appointment_id)
                appointment.visit_status = "PAYMENT_COMPLETE"
                appointment.save()

                return Response({
                    "status": "success",
                    "message": "Bill saved successfully"
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "status": "error",
                    "message": "Invalid data",
                    "errors": bill_serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except KeyError as e:
            return Response({
                "status": "error",
                "message": f"Missing required field: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentHistoryView(APIView):
    """
    Payment History & Reports API

    Purpose:
        Retrieves monthly payment history for patient and pharmacy bills.
        Provides aggregated totals by payment type.

    Methods:
        POST: Get payment history for specific month/year

    Request Body:
        month (int): Month (1-12)
        year (int): Year (e.g., 2025)

    Response:
        Returns:
        - List of bills (patient + pharmacy combined)
        - Totals by payment type (CASH, CARD, UPI, OTHER)
        - Separate totals for patient vs pharmacy
        - Combined overall totals

    Response Structure:
        {
            "month": int,
            "year": int,
            "bills": [...],  // Sorted by date
            "totals": {
                "patient": {...},
                "pharmacy": {...},
                "combined": {...}
            }
        }

    Related Models:
        - PatientBill: Patient bills (consultation + medicines)
        - PharmacyBilling: Direct pharmacy sales

    Business Logic:
        - Filters by bill_date range (month)
        - Only PAID bills included
        - User-specific (created_by filter)
        - Aggregates by payment_type
    """

    def post(self, request):
        """Get monthly payment history with aggregated totals"""
        try:
            month = request.data.get('month')
            year = request.data.get('year')

            # Validate required fields
            if not month or not year:
                return Response({
                    'error': 'Month and year are required.'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                month = int(month)
                year = int(year)
            except ValueError:
                return Response({
                    'error': 'Invalid month or year format.'
                }, status=status.HTTP_400_BAD_REQUEST)

            if month < 1 or month > 12:
                return Response({
                    'error': 'Invalid month value. Month must be between 1 and 12.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Calculate date range
            try:
                last_day = calendar.monthrange(year, month)[1]
                start_date = datetime(year, month, 1)
                end_date = datetime(year, month, last_day, 23, 59, 59, 999999)

                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(start_date)
                    end_date = timezone.make_aware(end_date)
            except (ValueError, calendar.IllegalMonthError):
                return Response({
                    'error': 'Invalid date values.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get bills
            patient_bills = PatientBill.objects.filter(
                bill_date__range=(start_date, end_date),
                payment_status='PAID',
                created_by=request.user
            )

            pharmacy_bills = PharmacyBilling.objects.filter(
                bill_date__range=(start_date, end_date),
                payment_status='PAID'
            )

            combined_bills = []
            patient_totals = defaultdict(float)
            pharmacy_totals = defaultdict(float)

            # Process Patient Bills
            for bill in patient_bills:
                patient = bill.appointment.patient if bill.appointment else None
                doctor = bill.appointment.doctor if bill.appointment else None

                # Enhance medicine items with medication_id and stock_entry_id for returns
                enhanced_items = []

                # Get all returns for this bill to calculate returned quantities
                bill_returns = PatientMedicineReturn.objects.filter(
                    patient_bill=bill,
                    is_refunded=True
                ).prefetch_related('items')

                # Build a map of returned quantities by medication_id and stock_entry_id
                returned_quantities = {}
                for return_obj in bill_returns:
                    for return_item in return_obj.items.all():
                        key = (return_item.medication_id, return_item.stock_entry_id)
                        returned_quantities[key] = returned_quantities.get(key, 0) + return_item.quantity_returned

                if bill.consultation:
                    # Get dispensed medicines with IDs from MedicationDispense
                    prescribed_medicines = PrescribedMedicine.objects.filter(
                        consultation=bill.consultation
                    ).select_related('medicine')

                    for prescribed in prescribed_medicines:
                        dispenses = MedicationDispense.objects.filter(
                            prescribed_medicine=prescribed
                        ).select_related('stock_entry', 'stock_entry__medication')

                        if dispenses.exists():
                            total_quantity = sum(d.quantity_dispensed for d in dispenses)
                            first_dispense = dispenses.first()

                            # Calculate returned quantity for this item
                            key = (prescribed.medicine.id, first_dispense.stock_entry.id if first_dispense.stock_entry else None)
                            quantity_returned = returned_quantities.get(key, 0)
                            returnable_quantity = max(0, total_quantity - quantity_returned)

                            enhanced_items.append({
                                'medication_id': prescribed.medicine.id,
                                'stock_entry_id': first_dispense.stock_entry.id if first_dispense.stock_entry else None,
                                'name': f"{prescribed.medicine.name} {prescribed.medicine.strength}",
                                'price': str(first_dispense.stock_entry.selling_price) if first_dispense.stock_entry else "0",
                                'quantity': total_quantity,
                                'quantity_returned': quantity_returned,
                                'returnable_quantity': returnable_quantity,
                                'total': str(first_dispense.stock_entry.selling_price * total_quantity) if first_dispense.stock_entry else "0"
                            })
                else:
                    # Fallback to stored JSON if no consultation data
                    enhanced_items = bill.medicine_items

                combined_bills.append({
                    "type": "patient",
                    "bill_id": bill.id,
                    "patient_id_fk": patient.id if patient else None,
                    "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "N/A",
                    "doctor_name": f"{doctor.user.first_name} {doctor.user.last_name}" if doctor else "N/A",
                    "bill_number": bill.bill_number,
                    "bill_date": bill.bill_date.isoformat(),
                    "total_amount": float(bill.total_bill_amount),
                    "payment_status": bill.payment_status,
                    "payment_type": bill.payment_type,
                    "items": enhanced_items,
                    "consultation_fee": float(bill.consultation_fee),
                    "patient_id": patient.patient_id if patient else "N/A",
                    "department": doctor.specialization.department.name if doctor else "N/A",
                    "total_amount_words": num_to_words(bill.total_bill_amount)
                })

                patient_totals[bill.payment_type] += float(bill.total_bill_amount)

            # Process Pharmacy Bills
            for bill in pharmacy_bills:
                # Enhance pharmacy items with medication_id and stock_entry_id for returns
                enhanced_pharmacy_items = []

                # Get all returns for this pharmacy bill to calculate returned quantities
                pharmacy_returns = PatientMedicineReturn.objects.filter(
                    pharmacy_bill=bill,
                    is_refunded=True
                ).prefetch_related('items')

                # Build a map of returned quantities by medication_id and stock_entry_id
                pharmacy_returned_quantities = {}
                for return_obj in pharmacy_returns:
                    for return_item in return_obj.items.all():
                        key = (return_item.medication_id, return_item.stock_entry_id)
                        pharmacy_returned_quantities[key] = pharmacy_returned_quantities.get(key, 0) + return_item.quantity_returned

                # Get items from PharmacyBillingItem model (has FKs to medication and stock)
                pharmacy_bill_items = PharmacyBillingItem.objects.filter(
                    billing=bill
                ).select_related('medication', 'stock_entry')

                for item in pharmacy_bill_items:
                    # Calculate returned quantity for this item
                    key = (item.medication.id, item.stock_entry.id if item.stock_entry else None)
                    quantity_returned = pharmacy_returned_quantities.get(key, 0)
                    returnable_quantity = max(0, item.quantity - quantity_returned)

                    enhanced_pharmacy_items.append({
                        'medication_id': item.medication.id,
                        'stock_entry_id': item.stock_entry.id if item.stock_entry else None,
                        'name': f"{item.medication.name} {item.medication.strength}",
                        'price': str(item.unit_price) if item.unit_price else "0",
                        'quantity': item.quantity,
                        'quantity_returned': quantity_returned,
                        'returnable_quantity': returnable_quantity,
                        'total': str(float(item.unit_price or 0) * item.quantity)
                    })

                # Fallback to JSON items if no PharmacyBillingItem records found
                if not enhanced_pharmacy_items:
                    enhanced_pharmacy_items = bill.items + bill.others

                combined_bills.append({
                    "type": "pharmacy",
                    "bill_id": bill.id,
                    "patient_name": bill.patient_name,
                    "doctor_name": "N/A",
                    "bill_number": bill.bill_number,
                    "bill_date": bill.bill_date.isoformat(),
                    "total_amount": float(bill.amount),
                    "payment_status": bill.payment_status,
                    "payment_type": bill.payment_type,
                    "items": enhanced_pharmacy_items,
                    "consultation_fee": 0.00,
                    "patient_id": "N/A",
                    "department": "Pharmacy",
                    "total_amount_words": num_to_words(bill.amount)
                })

                pharmacy_totals[bill.payment_type] += float(bill.amount)

            # Get all payment types
            payment_types = set().union(
                PatientBill._meta.get_field('payment_type').choices,
                PharmacyBilling._meta.get_field('payment_type').choices
            )

            # Create comprehensive totals
            full_totals = defaultdict(float)
            for pt in payment_types:
                code = pt[0]
                full_totals[code] = (
                    patient_totals.get(code, 0) +
                    pharmacy_totals.get(code, 0)
                )

            # Calculate overall totals
            patient_overall = sum(patient_totals.values())
            pharmacy_overall = sum(pharmacy_totals.values())
            combined_total = patient_overall + pharmacy_overall

            response_data = {
                'month': month,
                'year': year,
                'bills': sorted(combined_bills, key=lambda x: x['bill_date']),
                'totals': {
                    'patient': {
                        'by_payment_type': dict(patient_totals),
                        'overall': patient_overall
                    },
                    'pharmacy': {
                        'by_payment_type': dict(pharmacy_totals),
                        'overall': pharmacy_overall
                    },
                    'combined': {
                        'by_payment_type': dict(full_totals),
                        'overall': combined_total
                    }
                }
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# SECTION 6: DIRECT PHARMACY SALES (Walk-in Patients)
# ============================================================================
# Purpose: Direct medicine sales without prescription
# Related Models: PharmacyBilling, PharmacyBillingItem, MedicationStock
# Use Case: OTC medicines, walk-in patients, other pharmacy items
# ============================================================================


class Pharmacy_Items(APIView):
    """
    Direct Pharmacy Billing API (Walk-in Sales)

    Purpose:
        Handles direct pharmacy sales without prescription.
        Supports both medications and other items (non-medication).

    Methods:
        GET: Get next available bill number
        POST: Create pharmacy bill with items

    GET Response:
        Returns next pharmacy bill number

    POST Request Body:
        patient_name (str, optional): Patient name
        bill_date (date): Bill date
        payment_type (str): CASH/CARD/UPI/OTHER
        payment_status (str): PENDING/PAID/CANCELLED
        age (int, optional): Patient age
        gender (str, optional): Patient gender
        discount (decimal): Discount amount
        items (list): List of items
            For medication items:
                - medication (int): Medication ID
                - stock_entry (int): Stock entry ID
                - quantity (int): Quantity
                - unit_price (decimal): Price per unit
            For other items:
                - name (str): Item name
                - price (decimal): Price
                - quantity (int): Quantity

    Response:
        201: Bill created with details
        400: Validation error
        500: Server error

    Business Logic:
        1. Generate unique bill number
        2. Process discount
        3. Validate items (medication or other)
        4. Create PharmacyBilling record
        5. Create PharmacyBillingItem records for medications
        6. Store other items in JSON field
        7. Calculate totals and apply discount

    Related Models:
        - PharmacyBilling: Bill header
        - PharmacyBillingItem: Medication line items
        - MedicationStock: Stock entries
        - Medication: Medicine details

    Note: Stock quantity NOT deducted here (done by background task or manually)
    """

    # permission_classes = [IsPharmacist]

    @transaction.atomic
    def get(self, request):
        """Get next pharmacy bill number"""
        try:
            bill_number = get_next_pharma_bill_id()
            return Response({
                "bill_no": bill_number
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error generating bill number: {str(e)}")
            return Response({
                "error": "Failed to generate bill number"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Create pharmacy bill with medications and other items"""
        try:
            with transaction.atomic():
                data = request.data
                items = data.get('items', [])

                try:
                    bill_number = get_next_pharma_bill_id()
                    discount_data = Decimal(str(data.get('discount', 0)))
                except (ValueError, InvalidOperation):
                    discount_data = Decimal('0.00')

                if not items:
                    raise ValidationError("At least one item is required")

                # Create bill header
                bill = PharmacyBilling(
                    bill_number=bill_number,
                    patient_name=data.get('patient_name', ''),
                    bill_date=data.get('bill_date', datetime.now().date()),
                    dispensed_by=request.user,
                    payment_type=data.get('payment_type', 'CASH'),
                    payment_status=data.get('payment_status', 'PENDING'),
                    amount=Decimal('0.00'),
                    age=data.get('age') or None,
                    gender=data.get('gender') or None,
                    discount=discount_data,
                    items=[],
                    others=[]
                )
                bill.save()

                total_amount = Decimal('0.00')
                items_data = []
                others_data = []

                # Process each item
                for item in items:
                    # Type 1: Medication item
                    if 'medication' in item and 'stock_entry' in item:
                        required_med_fields = ['medication', 'stock_entry', 'quantity', 'unit_price']
                        if any(field not in item for field in required_med_fields):
                            raise ValidationError("Missing required fields in medication item")

                        try:
                            medication = Medication.objects.get(pk=item['medication'])
                            stock_entry = MedicationStock.objects.get(pk=item['stock_entry'])
                        except (Medication.DoesNotExist, MedicationStock.DoesNotExist):
                            raise ValidationError("Invalid medication or stock entry ID")

                        if stock_entry.medication != medication:
                            raise ValidationError(f"Stock entry {stock_entry.id} doesn't belong to medication {medication.id}")

                        try:
                            quantity = int(item['quantity'])
                            unit_price = Decimal(str(item['unit_price']))
                        except (ValueError, InvalidOperation):
                            raise ValidationError("Invalid quantity or price format")

                        if quantity <= 0 or unit_price <= Decimal('0'):
                            raise ValidationError("Quantity and price must be greater than 0")

                        # Create billing item
                        PharmacyBillingItem.objects.create(
                            billing=bill,
                            medication=medication,
                            stock_entry=stock_entry,
                            quantity=quantity,
                            unit_price=unit_price
                        )

                        item_price = unit_price * Decimal(quantity)
                        total_amount += item_price

                        items_data.append({
                            'medication_id': medication.id,
                            'stock_entry_id': stock_entry.id,
                            'name': str(medication),
                            'batch': stock_entry.batch_number,
                            'quantity': quantity,
                            'unit_price': float(unit_price),
                            'total': float(item_price)
                        })

                    # Type 2: Other item (non-medication)
                    else:
                        required_other_fields = ['name', 'price', 'quantity']
                        if any(field not in item for field in required_other_fields):
                            raise ValidationError("Missing required fields in other item")

                        try:
                            price = Decimal(str(item['price']))
                            quantity = int(item['quantity'])
                        except (InvalidOperation, ValueError):
                            raise ValidationError("Invalid price or quantity format in other item")

                        if price <= Decimal('0') or quantity <= 0:
                            raise ValidationError("Price and quantity must be greater than 0")

                        item_total = price * Decimal(quantity)
                        total_amount += item_total

                        others_data.append({
                            'name': item['name'],
                            'price': float(price),
                            'quantity': quantity,
                            'total': float(item_total),
                        })

                # Apply discount and save
                bill.amount = total_amount - bill.discount
                bill.items = items_data
                bill.others = others_data
                bill.save()

                return Response({
                    'id': bill.id,
                    'bill_number': bill.bill_number,
                    'patient_name': bill.patient_name,
                    'items': bill.items,
                    'others': bill.others,
                    'total_amount': float(total_amount),
                    'discount': float(bill.discount),
                    'final_amount': float(bill.amount),
                    'payment_status': bill.payment_status,
                    'payment_type': bill.payment_type
                }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Pharmacy billing error: {str(e)}")
            return Response({
                'error': f"Server error: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MedicationListView(APIView):
    """
    Medication Inventory Summary API

    Purpose:
        Provides complete medication inventory with stock levels.
        Shows available quantity after dispensing and billing.

    Methods:
        GET: List all medications with stock details

    Response:
        Returns list of medications with:
        - Basic medication details
        - Total quantity across all batches
        - Stock entries with:
            - Original quantity
            - Billed quantity (from pharmacy sales)
            - Dispensed quantity (from prescriptions)
            - Current available quantity
            - Batch details
            - Pricing

    Calculation Logic:
        For each stock entry:
        - original_quantity = stock.quantity
        - billed_quantity = sum(PharmacyBillingItem.quantity)
        - dispensed_quantity = sum(MedicationDispense.quantity_dispensed)
        - current_quantity = original - billed - dispensed

    Related Models:
        - Medication: Drug master
        - MedicationStock: Stock batches
        - PharmacyBillingItem: Direct sales
        - MedicationDispense: Prescription dispensing

    Use Case:
        - Inventory reports
        - Stock level monitoring
        - Reorder calculations
    """

    # permission_classes = [IsPharmacist]

    def get(self, request):
        """Get medication inventory with detailed stock breakdown"""
        try:
            medications = Medication.objects.prefetch_related(
                'stock_entries',
                'stock_entries__pharmacybillingitem_set',
                'stock_entries__medicationdispense_set'
            ).filter(is_active=True)

            medication_data = []

            for medication in medications:
                stock_entries = medication.stock_entries.all()

                # Calculate total quantity
                total_quantity = sum(entry.quantity for entry in stock_entries)

                # Get latest stock entry
                latest_stock = stock_entries.order_by('-received_date').first()

                med_info = {
                    'medication': medication.id,
                    'name': medication.name,
                    'description': medication.description,
                    'dosage_form': medication.dosage_form,
                    'strength': medication.strength,
                    'total_quantity': total_quantity,
                    'stock_entries': []
                }

                # Process each stock entry
                for stock in stock_entries:
                    original_quantity = stock.quantity

                    # Calculate billed quantity
                    billed_items = stock.pharmacybillingitem_set.all()
                    billed_quantity = sum(item.quantity for item in billed_items)

                    # Calculate dispensed quantity
                    dispensed_items = stock.medicationdispense_set.all()
                    dispensed_quant = sum(item.quantity_dispensed for item in dispensed_items)

                    # Total dispensed includes both billed and prescription dispenses
                    dispensed_quantity = dispensed_quant + billed_quantity

                    # Current available = original - billed - dispensed
                    current_quantity = original_quantity - billed_quantity - dispensed_quant

                    stock_info = {
                        'stock_entry': stock.id,
                        'batch_number': stock.batch_number,
                        'quantity': current_quantity,
                        'original_quantity': original_quantity,
                        'billed_quantity': billed_quantity,
                        'dispensed_quantity': dispensed_quantity,
                        'expiry_date': stock.expiry_date,
                        'received_date': stock.received_date,
                        'purchase_price': float(stock.purchase_price),
                        'selling_price': float(stock.selling_price),
                    }
                    med_info['stock_entries'].append(stock_info)

                medication_data.append(med_info)

            return Response({
                'status': 'success',
                'data': medication_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Medication list error: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch medication data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class DispensableMedicationView(APIView):
    """
    Dispensable Medication Inventory API

    Purpose:
        Returns ONLY medications with available stock for dispensing.
        Filters out medicines with zero quantity.

    Use Case:
        - Pharmacy counter: Show only medicines that can be dispensed
        - Stock selection: List available items for billing
        - Prevents selecting out-of-stock items

    Response:
        - Only medications with current_quantity > 0
        - Only stock entries with available quantity > 0
        - Excludes expired batches
    """
    def get(self, request):
        """Get dispensable medication inventory (only available stock)"""
        try:
            from django.utils import timezone
            today = timezone.now().date()

            medications = Medication.objects.prefetch_related(
                'stock_entries',
                'stock_entries__pharmacybillingitem_set',
                'stock_entries__medicationdispense_set'
            ).filter(is_active=True)

            medication_data = []

            for medication in medications:
                stock_entries = medication.stock_entries.filter(
                    is_active=True,
                    expiry_date__gt=today  # Exclude expired batches
                )

                available_stock_entries = []
                total_available_quantity = 0

                # Process each stock entry
                for stock in stock_entries:
                    original_quantity = stock.quantity

                    # Calculate billed quantity
                    billed_items = stock.pharmacybillingitem_set.all()
                    billed_quantity = sum(item.quantity for item in billed_items)

                    # Calculate dispensed quantity
                    dispensed_items = stock.medicationdispense_set.all()
                    dispensed_quant = sum(item.quantity_dispensed for item in dispensed_items)

                    # Total dispensed includes both billed and prescription dispenses
                    dispensed_quantity = dispensed_quant + billed_quantity

                    # Current available = original - billed - dispensed
                    current_quantity = original_quantity - billed_quantity - dispensed_quant

                    # Only include stock entries with available quantity
                    if current_quantity > 0:
                        stock_info = {
                            'stock_entry': stock.id,
                            'batch_number': stock.batch_number,
                            'quantity': current_quantity,
                            'original_quantity': original_quantity,
                            'billed_quantity': billed_quantity,
                            'dispensed_quantity': dispensed_quantity,
                            'expiry_date': stock.expiry_date,
                            'received_date': stock.received_date,
                            'purchase_price': float(stock.purchase_price),
                            'selling_price': float(stock.selling_price),
                        }
                        available_stock_entries.append(stock_info)
                        total_available_quantity += current_quantity

                # Only include medications with at least one available stock entry
                if available_stock_entries:
                    med_info = {
                        'medication': medication.id,
                        'name': medication.name,
                        'description': medication.description,
                        'dosage_form': medication.dosage_form,
                        'strength': medication.strength,
                        'total_quantity': total_available_quantity,
                        'stock_entries': available_stock_entries
                    }
                    medication_data.append(med_info)

            return Response({
                'status': 'success',
                'data': medication_data,
                'total_medications': len(medication_data)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Dispensable medication list error: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch dispensable medication data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class MedicationList(APIView):
    """
    Quick Medication Availability List API

    Purpose:
        Provides simple list of medications with total available quantity.
        Used for quick stock checks and search functionality.

    Methods:
        GET: List medications with availability

    Response:
        Returns simplified list:
        - medication ID
        - medication name
        - total available quantity (all batches combined)

    Calculation Logic:
        For each medication:
        - Get all stock entries
        - Calculate: available = quantity - dispensed - billed
        - Sum across all batches
        - Return max(total, 0) to avoid negatives

    Related Models:
        - Medication: Drug master
        - MedicationStock: Stock batches
        - MedicationDispense: Dispensing records
        - PharmacyBillingItem: Billing records

    Use Case:
        - Search autocomplete
        - Quick availability check
        - POS systems
    """

    def get(self, request):
        """Get simple medication list with total availability"""
        try:
            # Prefetch with aggregated quantities
            stock_prefetch = Prefetch(
                'stock_entries',
                queryset=MedicationStock.objects.annotate(
                    total_dispensed=Coalesce(
                        Sum('medicationdispense__quantity_dispensed'),
                        Value(0),
                        output_field=IntegerField()
                    ),
                    total_billed=Coalesce(
                        Sum('pharmacybillingitem__quantity'),
                        Value(0),
                        output_field=IntegerField()
                    )
                ).annotate(
                    available=F('quantity') - F('total_dispensed') - F('total_billed')
                )
            )

            medications = Medication.objects.prefetch_related(stock_prefetch)

            medication_data = []
            for med in medications:
                # Sum available quantity across all batches
                total_available = sum(
                    stock.available for stock in med.stock_entries.all()
                )

                medication_data.append({
                    'id': med.id,
                    'name': med.name,
                    'available_quantity': max(total_available, 0),
                })

            return Response({
                'status': 'success',
                'data': medication_data
            })

        except Exception as e:
            logger.error(f"Medication list error: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to retrieve medication data.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# SECTION 7: LABORATORY SERVICES & BILLING
# ============================================================================
# Purpose: Lab test billing and payment (similar to pharmacy)
# Related Models: LabBilling, LabDepartment, TestCategory, TestParameter
# Use Case: Lab test billing, sample collection charges
# ============================================================================


class Lab_Items(APIView):
    """
    Laboratory Services Billing API

    Purpose:
        Handles billing for laboratory tests and services.
        Similar to pharmacy billing but for lab services.

    Methods:
        GET: Get next available lab bill number
        POST: Create lab bill

    GET Response:
        Returns next lab bill number

    POST Request Body:
        bill_number (str): Bill number (optional, auto-generated if not provided)
        patient_name (str, optional): Patient name
        bill_date (date): Bill date
        payment_type (str): CASH/CARD/UPI/OTHER
        payment_status (str): PENDING/PAID/CANCELLED
        age (int, optional): Patient age
        gender (str, optional): Patient gender
        discount (decimal): Discount amount
        items (list): List of lab services
            - name (str): Service/test name
            - description (str, optional): Service description
            - price (decimal): Service price
            - quantity (int): Quantity (usually 1 for tests)

    Response:
        201: Bill created
        400: Validation error
        500: Server error

    Business Logic:
        1. Generate unique bill number
        2. Process discount
        3. Validate service items
        4. Create LabBilling record
        5. Store items in JSON field
        6. Calculate total and apply discount

    Related Models:
        - LabBilling: Lab bill record

    Note: This handles billing only. Actual test results managed separately.
    """

    # permission_classes = [IsLabTechnician]

    @transaction.atomic
    def get(self, request):
        """Get next lab bill number"""
        try:
            bill_number = get_next_lab_bill_id()
            return Response({
                "bill_no": bill_number
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error generating lab bill number: {str(e)}")
            return Response({
                'error': f"Server error: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Create lab services bill"""
        try:
            with transaction.atomic():
                data = request.data
                items = data.get('items', [])

                try:
                    discount_data = Decimal(str(data.get('discount', 0)))
                except (ValueError, InvalidOperation):
                    discount_data = Decimal('0.00')

                if not items:
                    raise ValidationError("At least one item is required")

                # Create bill
                bill = LabBilling(
                    bill_number=data.get('bill_number'),
                    patient_name=data.get('patient_name', ''),
                    bill_date=data.get('bill_date', datetime.now().date()),
                    dispensed_by=request.user,
                    payment_type=data.get('payment_type', 'CASH'),
                    payment_status=data.get('payment_status', 'PENDING'),
                    amount=Decimal('0.00'),
                    age=data.get('age') or None,
                    gender=data.get('gender') or None,
                    discount=discount_data,
                    items=[]
                )
                bill.save()

                total_amount = Decimal('0.00')
                items_data = []

                # Process lab service items
                for item in items:
                    required_fields = ['name', 'price', 'quantity']
                    if any(field not in item for field in required_fields):
                        raise ValidationError("Missing required fields in lab service item")

                    try:
                        price = Decimal(str(item['price']))
                        quantity = int(item['quantity'])
                    except (InvalidOperation, ValueError):
                        raise ValidationError("Invalid price or quantity format in lab service item")

                    if price <= Decimal('0') or quantity <= 0:
                        raise ValidationError("Price and quantity must be greater than 0")

                    item_total = price * Decimal(quantity)
                    total_amount += item_total

                    items_data.append({
                        'name': item['name'],
                        'description': item.get('description', ''),
                        'price': float(price),
                        'quantity': quantity,
                        'total': float(item_total),
                    })

                # Apply discount and save
                bill.amount = total_amount - bill.discount
                bill.items = items_data
                bill.save()

                return Response({
                    'id': bill.id,
                    'bill_number': bill.bill_number,
                    'patient_name': bill.patient_name,
                    'items': bill.items,
                    'total_amount': float(total_amount),
                    'discount': float(bill.discount),
                    'final_amount': float(bill.amount),
                    'payment_status': bill.payment_status,
                    'payment_type': bill.payment_type,
                    'bill_date': bill.bill_date,
                    'age': bill.age,
                    'gender': bill.gender
                }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Lab billing error: {str(e)}")
            return Response({
                'error': f"Server error: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# SECTION 8: LAB TEST CONFIGURATION MANAGEMENT
# ============================================================================
# Purpose: Configure lab test hierarchy (Departments → Categories → Parameters)
# Related Models: LabDepartment, TestCategory, TestParameter, ReferenceRange
# Use Case: Lab test master data setup
# ============================================================================


class DepartmentCreateView(APIView):
    """
    Lab Department Management API

    Purpose:
        Creates and lists laboratory departments.
        Departments organize test categories (e.g., Hematology, Biochemistry).

    Methods:
        GET: List all lab departments
        POST: Create new lab department

    GET Response:
        Returns list of departments with details

    POST Request Body:
        name (str): Department name (unique)
        code (str): Department code (unique, max 10 chars)
        description (str, optional): Department description
        rate (int, optional): Department-level base rate

    Response:
        GET: List of departments
        POST: Created department details
        400: Validation or duplicate error
        500: Server error

    Related Models:
        - LabDepartment: Department master
        - TestCategory: Categories under department

    Hierarchy:
        LabDepartment (e.g., Hematology)
        └── TestCategory (e.g., CBC)
            └── TestParameter (e.g., Hemoglobin)
                └── ReferenceRange (e.g., Male 13-17 g/dL)
    """

    # permission_classes = [IsAdminUser]

    def get(self, request):
        """List all lab departments"""
        try:
            departments = LabDepartment.objects.all().order_by('name')

            data = []
            for department in departments:
                data.append({
                    "id": department.id,
                    "name": department.name,
                    "code": department.code,
                    "description": department.description,
                    "rate":department.rate
                })

            return Response({
                "count": len(data),
                "status": "success",
                "departments": data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Create new lab department"""
        try:
            # Extract data
            name = request.data.get('name')
            code = request.data.get('code')
            description = request.data.get('description', '')
            rate = request.data.get('rate')

            # Manual validation
            if not name or not name.strip():
                return Response({
                    "status": "error",
                    "message": "Department name is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            if not code or not code.strip():
                return Response({
                    "status": "error",
                    "message": "Department code is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            if len(code.strip()) > 10:
                return Response({
                    "status": "error",
                    "message": "Department code cannot exceed 10 characters"
                }, status=status.HTTP_400_BAD_REQUEST)

            if rate is not None and (not isinstance(rate, int) or rate < 0):
                return Response({
                    "status": "error",
                    "message": "Rate must be a positive integer"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create department
            department = LabDepartment.objects.create(
                name=name.strip(),
                code=code.strip().upper(),
                description=description,
                rate=rate
            )

            return Response({
                "status": "success",
                "message": "Department created successfully",
                "department": {
                    "id": department.id,
                    "name": department.name,
                    "code": department.code,
                    "description": department.description,
                    "rate": department.rate
                }
            }, status=status.HTTP_201_CREATED)

        except IntegrityError as e:
            error_message = "Department with this name or code already exists"
            if 'name' in str(e):
                error_message = "Department with this name already exists"
            elif 'code' in str(e):
                error_message = "Department with this code already exists"

            return Response({
                "status": "error",
                "message": error_message
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, department_id):
        """Update lab department"""
        try:
            department = LabDepartment.objects.get(id=department_id)

            name = request.data.get('name')
            code = request.data.get('code')
            description = request.data.get('description')
            rate = request.data.get('rate')

            if name is not None:
                if not name.strip():
                    return Response({
                        "status": "error",
                        "message": "Department name cannot be empty"
                    }, status=status.HTTP_400_BAD_REQUEST)
                department.name = name.strip()

            if code is not None:
                if not code.strip():
                    return Response({
                        "status": "error",
                        "message": "Department code cannot be empty"
                    }, status=status.HTTP_400_BAD_REQUEST)
                if len(code.strip()) > 10:
                    return Response({
                        "status": "error",
                        "message": "Department code cannot exceed 10 characters"
                    }, status=status.HTTP_400_BAD_REQUEST)
                department.code = code.strip().upper()

            if description is not None:
                department.description = description

            if rate is not None:
                if not isinstance(rate, int) or rate < 0:
                    return Response({
                        "status": "error",
                        "message": "Rate must be a positive integer"
                    }, status=status.HTTP_400_BAD_REQUEST)
                department.rate = rate

            department.save()

            return Response({
                "status": "success",
                "message": "Department updated successfully",
            }, status=status.HTTP_200_OK)

        except LabDepartment.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Department not found"
            }, status=status.HTTP_404_NOT_FOUND)

        except IntegrityError as e:
            error_message = "Department with this name or code already exists"
            if 'name' in str(e):
                error_message = "Department with this name already exists"
            elif 'code' in str(e):
                error_message = "Department with this code already exists"

            return Response({
                "status": "error",
                "message": error_message
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestCategoryCreateView(APIView):
    """
    Test Category Management API

    Purpose:
        Creates and lists test categories within departments.
        Supports hierarchical categories (parent-child).

    Methods:
        GET: List test categories (with filters)
        POST: Create new test category

    GET Query Parameters:
        department_id (int, optional): Filter by department
        parent_id (int, optional): Filter by parent category
        parent_id=null: Get only main categories (no parent)

    POST Request Body:
        department (int): Department ID
        name (str): Category name
        code (str): Unique category code
        description (str, optional): Category description
        parent (int, optional): Parent category ID (for subcategories)

    Response:
        GET: List of categories with subcategory counts
        POST: Created category details
        400: Validation or duplicate error
        500: Server error

    Related Models:
        - TestCategory: Category master
        - LabDepartment: Parent department
        - TestParameter: Parameters under category

    Example Hierarchy:
        Hematology (Department)
        └── CBC (Category)
            ├── Hemoglobin (Parameter)
            ├── WBC (Parameter)
            └── RBC (Parameter)
    """

    # permission_classes = [IsAdminUser]

    def post(self, request):
        """Create new test category"""
        try:
            serializer = TestCategorySerializer(data=request.data)

            if not serializer.is_valid():
                return Response({
                    "status": "error",
                    "message": "Validation failed",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            validated_data = serializer.validated_data
            category = TestCategory.objects.create(
                department=validated_data['department'],
                name=validated_data['name'],
                code=validated_data['code'],
                description=validated_data.get('description', ''),
                parent=validated_data.get('parent')
            )

            return Response({
                "status": "success",
                "message": "Test category created successfully",
                "category": {
                    "id": category.id,
                    "name": category.name,
                    "code": category.code,
                    "description": category.description,
                    "department_id": category.department.id,
                    "department_name": category.department.name,
                    "parent_id": category.parent.id if category.parent else None,
                    "parent_name": category.parent.name if category.parent else None
                }
            }, status=status.HTTP_201_CREATED)

        except IntegrityError as e:
            error_message = "Test category already exists"
            if 'code' in str(e):
                error_message = "Test category with this code already exists"
            elif 'department' in str(e) and 'name' in str(e):
                error_message = "Test category with this name already exists in this department"

            return Response({
                "status": "error",
                "message": error_message
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        """List test categories with filters"""
        try:
            department_id = request.query_params.get('department_id')
            parent_id = request.query_params.get('parent_id')

            categories = TestCategory.objects.select_related(
                'department',
                'parent'
            ).all()


            if department_id:
                categories = categories.filter(department_id=department_id)

            if parent_id:
                categories = categories.filter(parent_id=parent_id)
            elif parent_id is None and 'parent_id' in request.query_params:
                categories = categories.filter(parent__isnull=True)

            categories = categories.order_by('department__name', 'name')


            departments_dict = defaultdict(lambda: {"categories": []})

            for category in categories:
                dept_id = category.department.id
                if "department_id" not in departments_dict[dept_id]:
                    departments_dict[dept_id]["department_id"] = dept_id
                    departments_dict[dept_id]["department_name"] = category.department.name

                departments_dict[dept_id]["categories"].append({
                    "id": category.id,
                    "name": category.name,
                    "code": category.code,
                    "description": category.description,
                    "parent_id": category.parent.id if category.parent else None,
                    "parent_name": category.parent.name if category.parent else None,
                    "subcategories_count": category.subcategories.count(),
                    "department_id":category.department.id,
                    "department_name":category.department.name
                })


            data = list(departments_dict.values())

            return Response({
                "count": len(categories),
                "status": "success",
                "departments": data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, category_id):
        """Update test category"""
        try:
            category = TestCategory.objects.get(id=category_id)

            department = request.data.get('department')
            name = request.data.get('name')
            code = request.data.get('code')
            description = request.data.get('description')
            parent = request.data.get('parent')

            if department is not None:
                try:
                    dept_obj = LabDepartment.objects.get(id=department)
                    category.department = dept_obj
                except LabDepartment.DoesNotExist:
                    return Response({
                        "status": "error",
                        "message": "Department not found"
                    }, status=status.HTTP_400_BAD_REQUEST)

            if name is not None:
                if not name.strip():
                    return Response({
                        "status": "error",
                        "message": "Category name cannot be empty"
                    }, status=status.HTTP_400_BAD_REQUEST)
                category.name = name.strip()

            if code is not None:
                if not code.strip():
                    return Response({
                        "status": "error",
                        "message": "Category code cannot be empty"
                    }, status=status.HTTP_400_BAD_REQUEST)
                if len(code.strip()) > 20:
                    return Response({
                        "status": "error",
                        "message": "Category code cannot exceed 20 characters"
                    }, status=status.HTTP_400_BAD_REQUEST)
                category.code = code.strip().upper()

            if description is not None:
                category.description = description

            if parent is not None:
                if parent:
                    try:
                        parent_obj = TestCategory.objects.get(id=parent)
                        if parent_obj.parent:
                            return Response({
                                "status": "error",
                                "message": "Cannot create subcategory under another subcategory"
                            }, status=status.HTTP_400_BAD_REQUEST)
                        category.parent = parent_obj
                    except TestCategory.DoesNotExist:
                        return Response({
                            "status": "error",
                            "message": "Parent category not found"
                        }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    category.parent = None

            category.save()

            return Response({
                "status": "success",
                "message": "Test category updated successfully",
                "category": {
                    "id": category.id,
                    "name": category.name,
                    "code": category.code,
                    "description": category.description,
                    "department_id": category.department.id,
                    "department_name": category.department.name,
                    "parent_id": category.parent.id if category.parent else None,
                    "parent_name": category.parent.name if category.parent else None
                }
            }, status=status.HTTP_200_OK)

        except TestCategory.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Test category not found"
            }, status=status.HTTP_404_NOT_FOUND)

        except IntegrityError as e:
            error_message = "Test category already exists"
            if 'code' in str(e):
                error_message = "Test category with this code already exists"
            elif 'department' in str(e) and 'name' in str(e):
                error_message = "Test category with this name already exists in this department"

            return Response({
                "status": "error",
                "message": error_message
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestParameterCreateView(APIView):
    """
    Test Parameter Management API

    Purpose:
        Creates and lists individual test parameters within categories.
        Parameters are the actual measurable values (e.g., Hemoglobin, WBC).

    Methods:
        GET: List test parameters (with filters)
        POST: Create new test parameter

    GET Query Parameters:
        category_id (int, optional): Filter by category
        is_active (bool, optional): Filter by active status

    POST Request Body:
        category (int): Category ID
        name (str): Parameter name
        code (str): Parameter code (unique within category)
        unit (str, optional): Measurement unit (e.g., 'g/dL', 'cells/μL')
        is_qualitative (bool): True for qualitative tests (Positive/Negative)
        normal_values (json, optional): Normal value ranges
        sequence_order (int): Display order in reports
        is_active (bool): Active status

    Response:
        GET: List of parameters with reference range counts
        POST: Created parameter details
        400: Validation or duplicate error
        500: Server error

    Related Models:
        - TestParameter: Parameter master
        - TestCategory: Parent category
        - ReferenceRange: Normal value ranges

    Example:
        Hemoglobin (Parameter)
        - Unit: g/dL
        - Quantitative test
        - Reference ranges by age/gender
    """

    # permission_classes = [IsAdminUser]

    def post(self, request):
        """Create new test parameter"""
        try:
            serializer = TestParameterSerializer(data=request.data)

            if not serializer.is_valid():
                return Response({
                    "status": "error",
                    "message": "Validation failed",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            validated_data = serializer.validated_data
            parameter = TestParameter.objects.create(
                category=validated_data['category'],
                name=validated_data['name'],
                code=validated_data['code'],
                unit=validated_data.get('unit', ''),
                is_qualitative=validated_data.get('is_qualitative', False),
                normal_values=validated_data.get('normal_values'),
                sequence_order=validated_data.get('sequence_order', 1),
                is_active=validated_data.get('is_active', True)
            )

            return Response({
                "status": "success",
                "message": "Test parameter created successfully",
                "parameter": {
                    "id": parameter.id,
                    "name": parameter.name,
                    "code": parameter.code,
                    "unit": parameter.unit,
                    "is_qualitative": parameter.is_qualitative,
                    "normal_values": parameter.normal_values,
                    "sequence_order": parameter.sequence_order,
                    "is_active": parameter.is_active,
                    "category_id": parameter.category.id,
                    "category_name": parameter.category.name
                }
            }, status=status.HTTP_201_CREATED)

        except IntegrityError as e:
            error_message = "Test parameter with this code already exists in this category"
            return Response({
                "status": "error",
                "message": error_message
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        """List test parameters with filters"""
        try:
            category_id = request.query_params.get('category_id')
            is_active = request.query_params.get('is_active')

            parameters = TestParameter.objects.select_related('category').all()

            # Apply filters
            if category_id:
                parameters = parameters.filter(category_id=category_id)

            if is_active is not None:
                parameters = parameters.filter(is_active=is_active.lower() == 'true')

            parameters = parameters.order_by('sequence_order', 'name')
            test_parameter_dict = defaultdict(lambda: {"parameters": []})



            data = []
            for parameter in parameters:
                    category_id = parameter.category.id
                    if "category_id" not in test_parameter_dict[category_id]:
                        test_parameter_dict[category_id]["category_id"] = category_id
                        test_parameter_dict[category_id]["category_name"] = parameter.category.name
                    test_parameter_dict[category_id]["parameters"].append({
                    "id": parameter.id,
                    "name": parameter.name,
                    "code": parameter.code,
                    "unit": parameter.unit,
                    "is_qualitative": parameter.is_qualitative,
                    "normal_values": parameter.normal_values,
                    "sequence_order": parameter.sequence_order,
                    "is_active": parameter.is_active,
                    "category_id": parameter.category.id,
                    "category_name": parameter.category.name,
                    "reference_ranges_count": parameter.reference_ranges.count()
                    })
            data = list(test_parameter_dict.values())

            return Response({
                "count": len(data),
                "status": "success",
                "category": data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, parameter_id):
        """Update test parameter"""
        try:
            parameter = TestParameter.objects.get(id=parameter_id)

            category = request.data.get('category')
            name = request.data.get('name')
            code = request.data.get('code')
            unit = request.data.get('unit')
            is_qualitative = request.data.get('is_qualitative')
            normal_values = request.data.get('normal_values')
            sequence_order = request.data.get('sequence_order')
            is_active = request.data.get('is_active')

            if category is not None:
                try:
                    cat_obj = TestCategory.objects.get(id=category)
                    parameter.category = cat_obj
                except TestCategory.DoesNotExist:
                    return Response({
                        "status": "error",
                        "message": "Category not found"
                    }, status=status.HTTP_400_BAD_REQUEST)

            if name is not None:
                if not name.strip():
                    return Response({
                        "status": "error",
                        "message": "Parameter name cannot be empty"
                    }, status=status.HTTP_400_BAD_REQUEST)
                parameter.name = name.strip()

            if code is not None:
                if not code.strip():
                    return Response({
                        "status": "error",
                        "message": "Parameter code cannot be empty"
                    }, status=status.HTTP_400_BAD_REQUEST)
                if len(code.strip()) > 20:
                    return Response({
                        "status": "error",
                        "message": "Parameter code cannot exceed 20 characters"
                    }, status=status.HTTP_400_BAD_REQUEST)
                parameter.code = code.strip().upper()

            if unit is not None:
                parameter.unit = unit

            if is_qualitative is not None:
                parameter.is_qualitative = is_qualitative

            if normal_values is not None:
                parameter.normal_values = normal_values

            if sequence_order is not None:
                if sequence_order < 1:
                    return Response({
                        "status": "error",
                        "message": "Sequence order must be at least 1"
                    }, status=status.HTTP_400_BAD_REQUEST)
                parameter.sequence_order = sequence_order

            if is_active is not None:
                parameter.is_active = is_active

            parameter.save()

            return Response({
                "status": "success",
                "message": "Test parameter updated successfully",
                "parameter": {
                    "id": parameter.id,
                    "name": parameter.name,
                    "code": parameter.code,
                    "unit": parameter.unit,
                    "is_qualitative": parameter.is_qualitative,
                    "normal_values": parameter.normal_values,
                    "sequence_order": parameter.sequence_order,
                    "is_active": parameter.is_active,
                    "category_id": parameter.category.id,
                    "category_name": parameter.category.name
                }
            }, status=status.HTTP_200_OK)

        except TestParameter.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Test parameter not found"
            }, status=status.HTTP_404_NOT_FOUND)

        except IntegrityError:
            return Response({
                "status": "error",
                "message": "Test parameter with this code already exists in this category"
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReferenceRangeCreateView(APIView):
    """
    Reference Range Management API

    Purpose:
        Creates and lists reference (normal) ranges for test parameters.
        Supports age and gender-specific ranges.

    Methods:
        GET: List reference ranges (with filters)
        POST: Create new reference range

    GET Query Parameters:
        parameter_id (int, optional): Filter by parameter
        gender (str, optional): Filter by gender

    POST Request Body:
        parameter (int): Parameter ID
        gender (str, optional): Gender (Male/Female/Other)
        age_min (int, optional): Minimum age
        age_max (int, optional): Maximum age
        min_val (float): Minimum normal value
        max_val (float): Maximum normal value
        note (str, optional): Additional notes

    Response:
        GET: List of reference ranges with formatted display
        POST: Created reference range details
        400: Validation error
        500: Server error

    Related Models:
        - ReferenceRange: Range definition
        - TestParameter: Parent parameter

    Example:
        Hemoglobin
        - Male, 18-65 years: 13.5 - 17.5 g/dL
        - Female, 18-65 years: 12.0 - 15.5 g/dL
        - Children, 5-12 years: 11.5 - 15.5 g/dL

    Use Case:
        - Lab result interpretation
        - Flagging abnormal values
        - Report generation
    """

    # permission_classes = [IsAdminUser]

    def post(self, request):
        """Create new reference range"""
        try:
            serializer = ReferenceRangeSerializer(data=request.data)

            if not serializer.is_valid():
                return Response({
                    "status": "error",
                    "message": "Validation failed",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            validated_data = serializer.validated_data
            reference_range = ReferenceRange.objects.create(
                parameter=validated_data['parameter'],
                gender=validated_data.get('gender'),
                age_min=validated_data.get('age_min'),
                age_max=validated_data.get('age_max'),
                min_val=validated_data['min_val'],
                max_val=validated_data['max_val'],
                note=validated_data.get('note', '')
            )

            return Response({
                "status": "success",
                "message": "Reference range created successfully",
                "reference_range": {
                    "id": reference_range.id,
                    "gender": reference_range.gender,
                    "age_min": reference_range.age_min,
                    "age_max": reference_range.age_max,
                    "min_val": reference_range.min_val,
                    "max_val": reference_range.max_val,
                    "note": reference_range.note,
                    "parameter_id": reference_range.parameter.id,
                    "parameter_name": reference_range.parameter.name,
                    "parameter_unit": reference_range.parameter.unit
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        """List reference ranges with filters"""
        try:
            parameter_id = request.query_params.get('parameter_id')
            gender = request.query_params.get('gender')

            ranges = ReferenceRange.objects.select_related('parameter').all()

            # Apply filters
            if parameter_id:
                ranges = ranges.filter(parameter_id=parameter_id)

            if gender:
                ranges = ranges.filter(gender=gender)

            ranges = ranges.order_by('parameter__name', 'age_min')
            parameter_dict = defaultdict(lambda: {"reference_ranges": []})

            data = []
            for range_obj in ranges:
                    parameter_id = range_obj.parameter.id
                    if parameter_id not in parameter_dict[parameter_id]:
                        parameter_dict[parameter_id]["parameter_id"] = parameter_id
                        parameter_dict[parameter_id]["parameter_name"] = range_obj.parameter.name

                    parameter_dict[parameter_id]["reference_ranges"].append({
                    "id": range_obj.id,
                    "gender": range_obj.gender,
                    "age_min": range_obj.age_min,
                    "age_max": range_obj.age_max,
                    "min_val": range_obj.min_val,
                    "max_val": range_obj.max_val,
                    "note": range_obj.note,
                    "parameter_id": range_obj.parameter.id,
                    "parameter_name": range_obj.parameter.name,
                    "parameter_unit": range_obj.parameter.unit,
                    "age_range_display": f"{range_obj.age_min or 0}-{range_obj.age_max or '∞'} years",
                    "range_display": f"{range_obj.min_val} - {range_obj.max_val} {range_obj.parameter.unit}",
                    })

            data = list(parameter_dict.values())



            return Response({
                "count": len(data),
                "status": "success",
                "parameter": data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, range_id):
        """Update reference range"""
        try:
            reference_range = ReferenceRange.objects.get(id=range_id)

            parameter = request.data.get('parameter')
            gender = request.data.get('gender')
            age_min = request.data.get('age_min')
            age_max = request.data.get('age_max')
            min_val = request.data.get('min_val')
            max_val = request.data.get('max_val')
            note = request.data.get('note')

            if parameter is not None:
                try:
                    param_obj = TestParameter.objects.get(id=parameter)
                    reference_range.parameter = param_obj
                except TestParameter.DoesNotExist:
                    return Response({
                        "status": "error",
                        "message": "Parameter not found"
                    }, status=status.HTTP_400_BAD_REQUEST)

            if gender is not None:
                reference_range.gender = gender

            if age_min is not None:
                reference_range.age_min = age_min

            if age_max is not None:
                reference_range.age_max = age_max

            if min_val is not None:
                reference_range.min_val = min_val

            if max_val is not None:
                reference_range.max_val = max_val

            if min_val is not None and max_val is not None:
                if min_val >= max_val:
                    return Response({
                        "status": "error",
                        "message": "Minimum value must be less than maximum value"
                    }, status=status.HTTP_400_BAD_REQUEST)
            elif min_val is not None and reference_range.max_val:
                if min_val >= reference_range.max_val:
                    return Response({
                        "status": "error",
                        "message": "Minimum value must be less than maximum value"
                    }, status=status.HTTP_400_BAD_REQUEST)
            elif max_val is not None and reference_range.min_val:
                if reference_range.min_val >= max_val:
                    return Response({
                        "status": "error",
                        "message": "Minimum value must be less than maximum value"
                    }, status=status.HTTP_400_BAD_REQUEST)

            if age_min is not None and age_max is not None:
                if age_min >= age_max:
                    return Response({
                        "status": "error",
                        "message": "Minimum age must be less than maximum age"
                    }, status=status.HTTP_400_BAD_REQUEST)
            elif age_min is not None and reference_range.age_max:
                if age_min >= reference_range.age_max:
                    return Response({
                        "status": "error",
                        "message": "Minimum age must be less than maximum age"
                    }, status=status.HTTP_400_BAD_REQUEST)
            elif age_max is not None and reference_range.age_min:
                if reference_range.age_min >= age_max:
                    return Response({
                        "status": "error",
                        "message": "Minimum age must be less than maximum age"
                    }, status=status.HTTP_400_BAD_REQUEST)

            if note is not None:
                reference_range.note = note

            reference_range.save()

            return Response({
                "status": "success",
                "message": "Reference range updated successfully",
                "reference_range": {
                    "id": reference_range.id,
                    "gender": reference_range.gender,
                    "age_min": reference_range.age_min,
                    "age_max": reference_range.age_max,
                    "min_val": reference_range.min_val,
                    "max_val": reference_range.max_val,
                    "note": reference_range.note,
                    "parameter_id": reference_range.parameter.id,
                    "parameter_name": reference_range.parameter.name,
                    "parameter_unit": reference_range.parameter.unit
                }
            }, status=status.HTTP_200_OK)

        except ReferenceRange.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Reference range not found"
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LabDepartmentSerializerView(APIView):
    """
    Complete Lab Test Hierarchy API (Optimized)

    Purpose:
        Returns complete lab test structure in one call.
        Includes departments → categories → parameters → ranges.

    Methods:
        GET: Get complete hierarchy (with optional department filter)

    Query Parameters:
        department_id (int, optional): Filter specific department

    Response:
        Returns nested structure:
        - Departments
            - Categories
                - Subcategories
                    - Parameters
                        - Reference Ranges

    Optimization:
        Uses prefetch_related for efficient querying
        Prevents N+1 query problem

    Related Models:
        - LabDepartment
        - TestCategory
        - TestParameter
        - ReferenceRange

    Use Case:
        - Lab test selection UI
        - Complete catalog export
        - Test configuration review
    """

    # permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get complete lab test hierarchy"""
        try:
            department_id = request.query_params.get('department_id')

            # Optimized query with prefetch
            departments = LabDepartment.objects.prefetch_related(
                'categories__subcategories__parameters__reference_ranges',
                'categories__parameters__reference_ranges'
            ).all()

            if department_id:
                departments = departments.filter(id=department_id)

            departments = departments.order_by('name')

            # Serialize complete hierarchy
            serializer = LabDepartmentSerializer(departments, many=True)

            return Response({
                "count": len(serializer.data),
                "status": "success",
                "departments": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# SECTION 9: AUDIT LOG & HISTORY TRACKING
# ============================================================================
# Purpose: Track all medication stock changes for audit and compliance
# Related Models: MedicationStock
# Use Case: Audit trail, compliance reporting, change tracking
# ============================================================================


class MedicationStockAuditLogView(APIView):
    """
    Medication Stock Audit Log API

    Purpose:
        Provides complete audit trail for medication stock changes.
        Shows who created/updated stock entries and when.

    Methods:
        GET: Retrieve audit logs for stock entries

    Query Parameters:
        stock_id (int, optional): Filter by specific stock entry
        medication_id (int, optional): Filter by medication
        start_date (date, optional): Filter from date
        end_date (date, optional): Filter to date
        updated_by (int, optional): Filter by user who made changes

    Response:
        Returns list of stock entries with complete audit information:
        - Stock details
        - Medication information
        - Created by (user name, date)
        - Updated by (user name, date)
        - All changes made

    Use Cases:
        - Compliance audits
        - Track price changes
        - Monitor stock adjustments
        - Identify who made specific changes
    """

    # permission_classes = [IsPharmacist]

    def get(self, request):
        """Get audit logs for medication stock"""
        try:
            # Start with all stock entries
            queryset = MedicationStock.objects.select_related(
                'medication',
                'created_by',
                'updated_by'
            ).all()

            # Apply filters
            stock_id = request.query_params.get('stock_id')
            if stock_id:
                queryset = queryset.filter(id=stock_id)

            medication_id = request.query_params.get('medication_id')
            if medication_id:
                queryset = queryset.filter(medication_id=medication_id)

            start_date = request.query_params.get('start_date')
            if start_date:
                queryset = queryset.filter(updated_on__gte=start_date)

            end_date = request.query_params.get('end_date')
            if end_date:
                queryset = queryset.filter(updated_on__lte=end_date)

            updated_by = request.query_params.get('updated_by')
            if updated_by:
                queryset = queryset.filter(updated_by_id=updated_by)

            # Order by most recently updated
            queryset = queryset.order_by('-updated_on', '-created_on')

            # Build audit log response
            audit_logs = []
            for stock in queryset:
                log_entry = {
                    'stock_id': stock.id,
                    'medication': {
                        'id': stock.medication.id,
                        'name': stock.medication.name,
                        'dosage_form': stock.medication.dosage_form,
                        'strength': stock.medication.strength,
                    },
                    'batch_number': stock.batch_number,
                    'current_quantity': stock.quantity,
                    'expiry_date': stock.expiry_date,
                    'audit_trail': {
                        'created_by': stock.created_by.get_full_name() if stock.created_by else None,
                        'created_by_id': stock.created_by.id if stock.created_by else None,
                        'created_on': stock.created_on,
                        'updated_by': stock.updated_by.get_full_name() if stock.updated_by else None,
                        'updated_by_id': stock.updated_by.id if stock.updated_by else None,
                        'updated_on': stock.updated_on,
                        'last_modified': stock.updated_on if stock.updated_on else stock.created_on,
                    },
                    'stock_details': {
                        'opening_quantity': stock.opening_quantity,
                        'received_quantity': stock.received_quantity,
                        'sold_quantity': stock.sold_quantity,
                        'returned_quantity': stock.returned_quantity,
                        'damaged_quantity': stock.damaged_quantity,
                        'adjusted_quantity': stock.adjusted_quantity,
                    },
                    'pricing': {
                        'purchase_price': str(stock.purchase_price),
                        'selling_price': str(stock.selling_price),
                        'mrp': str(stock.mrp) if stock.mrp else None,
                    },
                    'supplier': stock.supplier,
                    'manufacturer': stock.manufacturer,
                    'is_active': stock.is_active,
                    'status_flags': {
                        'is_expired': stock.is_expired,
                        'is_near_expiry': stock.is_near_expiry,
                        'is_low_stock': stock.is_low_stock,
                        'is_out_of_stock': stock.is_out_of_stock,
                    }
                }
                audit_logs.append(log_entry)

            return Response({
                'status': 'success',
                'count': len(audit_logs),
                'audit_logs': audit_logs
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to fetch audit logs: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Failed to fetch audit logs: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# SECTION 10: INVENTORY REPORTS & ANALYTICS
# ============================================================================
# Purpose: Comprehensive inventory analytics and reporting
# Related Models: MedicationStock, Medication, MedicationDispense, PharmacyBilling
# Use Case: Business intelligence, inventory optimization, decision making
# ============================================================================


class InventoryValuationReportView(APIView):
    """
    Inventory Valuation Report API

    Purpose:
        Calculate total inventory value and provide stock valuation metrics.
        Shows current stock value based on purchase and selling prices.

    Methods:
        GET: Get inventory valuation report

    Query Parameters:
        medication_id (int, optional): Filter by specific medication

    Response:
        Returns:
        - Total inventory value (purchase price)
        - Total inventory value (selling price)
        - Potential profit
        - Stock breakdown by medication
        - Total items in stock

    Use Cases:
        - Financial reporting
        - Stock valuation for accounting
        - Profit margin analysis
    """

    # permission_classes = [IsPharmacist]

    def get(self, request):
        """Get inventory valuation report"""
        try:
            # Filter active stock entries
            queryset = MedicationStock.objects.select_related('medication').filter(
                is_active=True,
                medication__is_active=True
            )

            medication_id = request.query_params.get('medication_id')
            if medication_id:
                queryset = queryset.filter(medication_id=medication_id)

            total_purchase_value = Decimal('0.00')
            total_selling_value = Decimal('0.00')
            medication_breakdown = []
            total_items = 0

            for stock in queryset:
                # Calculate current stock (after dispensing)
                current_stock = stock.get_current_stock()

                if current_stock > 0:
                    purchase_value = stock.purchase_price * current_stock
                    selling_value = stock.selling_price * current_stock
                    profit_margin = selling_value - purchase_value

                    total_purchase_value += purchase_value
                    total_selling_value += selling_value
                    total_items += current_stock

                    medication_breakdown.append({
                        'medication_id': stock.medication.id,
                        'medication_name': stock.medication.name,
                        'dosage_form': stock.medication.dosage_form,
                        'strength': stock.medication.strength,
                        'batch_number': stock.batch_number,
                        'current_stock': current_stock,
                        'purchase_price': str(stock.purchase_price),
                        'selling_price': str(stock.selling_price),
                        'purchase_value': str(purchase_value),
                        'selling_value': str(selling_value),
                        'potential_profit': str(profit_margin),
                        'profit_percentage': str(round((profit_margin / purchase_value * 100), 2)) if purchase_value > 0 else '0.00',
                        'expiry_date': stock.expiry_date,
                    })

            return Response({
                'status': 'success',
                'summary': {
                    'total_purchase_value': str(total_purchase_value),
                    'total_selling_value': str(total_selling_value),
                    'total_potential_profit': str(total_selling_value - total_purchase_value),
                    'overall_profit_margin': str(round(((total_selling_value - total_purchase_value) / total_purchase_value * 100), 2)) if total_purchase_value > 0 else '0.00',
                    'total_items_in_stock': total_items,
                    'unique_medications': len(set([item['medication_id'] for item in medication_breakdown])),
                },
                'breakdown': medication_breakdown
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Inventory valuation report error: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Failed to generate inventory valuation report: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FastMovingMedicationsReportView(APIView):
    """
    Fast Moving Medications Report API

    Purpose:
        Identify top-selling/most dispensed medications.
        Helps with inventory planning and procurement decisions.

    Methods:
        GET: Get fast moving medications

    Query Parameters:
        days (int, optional): Number of days to analyze (default: 30)
        limit (int, optional): Number of top items to return (default: 20)

    Response:
        Returns list of medications sorted by quantity sold:
        - Medication details
        - Total quantity sold
        - Number of times dispensed
        - Revenue generated
        - Average daily sales

    Use Cases:
        - Inventory planning
        - Identify popular medications
        - Stock optimization
    """

    # permission_classes = [IsPharmacist]

    def get(self, request):
        """Get fast moving medications report"""
        try:
            days = int(request.query_params.get('days', 30))
            limit = int(request.query_params.get('limit', 20))

            from_date = timezone.now() - timedelta(days=days)

            # Aggregate sold quantities from MedicationStock
            fast_moving = MedicationStock.objects.select_related('medication').filter(
                is_active=True,
                medication__is_active=True,
                updated_on__gte=from_date
            ).values(
                'medication__id',
                'medication__name',
                'medication__dosage_form',
                'medication__strength'
            ).annotate(
                total_sold=Sum('sold_quantity'),
                total_revenue=Sum(F('sold_quantity') * F('selling_price'))
            ).filter(
                total_sold__gt=0
            ).order_by('-total_sold')[:limit]

            result = []
            for item in fast_moving:
                avg_daily_sales = item['total_sold'] / days if days > 0 else 0

                result.append({
                    'medication_id': item['medication__id'],
                    'medication_name': item['medication__name'],
                    'dosage_form': item['medication__dosage_form'],
                    'strength': item['medication__strength'],
                    'total_quantity_sold': item['total_sold'],
                    'total_revenue': str(item['total_revenue']) if item['total_revenue'] else '0.00',
                    'average_daily_sales': round(avg_daily_sales, 2),
                    'analysis_period_days': days,
                })

            return Response({
                'status': 'success',
                'period': f'Last {days} days',
                'count': len(result),
                'fast_moving_medications': result
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Fast moving medications report error: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Failed to generate fast moving report: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SlowMovingMedicationsReportView(APIView):
    """
    Slow Moving Medications Report API

    Purpose:
        Identify medications with low sales/dispensing.
        Helps identify dead stock and optimize inventory.

    Methods:
        GET: Get slow moving medications

    Query Parameters:
        days (int, optional): Number of days to analyze (default: 90)
        max_sales (int, optional): Maximum sales threshold (default: 5)

    Response:
        Returns list of slow-moving medications:
        - Medication details
        - Current stock quantity
        - Quantity sold in period
        - Stock value
        - Days in inventory

    Use Cases:
        - Identify dead stock
        - Reduce inventory carrying costs
        - Plan clearance sales
    """

    # permission_classes = [IsPharmacist]

    def get(self, request):
        """Get slow moving medications report"""
        try:
            days = int(request.query_params.get('days', 90))
            max_sales = int(request.query_params.get('max_sales', 5))

            from_date = timezone.now() - timedelta(days=days)

            # Find medications with low sales
            slow_moving = MedicationStock.objects.select_related('medication').filter(
                is_active=True,
                medication__is_active=True,
                received_date__lte=from_date
            ).annotate(
                current_stock=F('opening_quantity') + F('received_quantity') -
                              F('sold_quantity') - F('returned_quantity') -
                              F('damaged_quantity') + F('adjusted_quantity')
            ).filter(
                sold_quantity__lte=max_sales,
                current_stock__gt=0
            ).order_by('sold_quantity', '-current_stock')

            result = []
            for stock in slow_moving:
                current_stock = stock.get_current_stock()
                stock_value = stock.purchase_price * current_stock
                days_in_inventory = (timezone.now().date() - stock.received_date).days

                result.append({
                    'stock_id': stock.id,
                    'medication_id': stock.medication.id,
                    'medication_name': stock.medication.name,
                    'dosage_form': stock.medication.dosage_form,
                    'strength': stock.medication.strength,
                    'batch_number': stock.batch_number,
                    'current_stock': current_stock,
                    'quantity_sold': stock.sold_quantity,
                    'stock_value': str(stock_value),
                    'purchase_price': str(stock.purchase_price),
                    'selling_price': str(stock.selling_price),
                    'received_date': stock.received_date,
                    'expiry_date': stock.expiry_date,
                    'days_in_inventory': days_in_inventory,
                    'is_near_expiry': stock.is_near_expiry,
                })

            total_dead_stock_value = sum([Decimal(item['stock_value']) for item in result])

            return Response({
                'status': 'success',
                'period': f'Last {days} days',
                'criteria': f'Sales <= {max_sales} units',
                'count': len(result),
                'total_dead_stock_value': str(total_dead_stock_value),
                'slow_moving_medications': result
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Slow moving medications report error: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Failed to generate slow moving report: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StockAgingReportView(APIView):
    """
    Stock Aging Report API

    Purpose:
        Analyze stock age and identify old inventory.
        Shows how long stock has been sitting in inventory.

    Methods:
        GET: Get stock aging report

    Response:
        Returns stock categorized by age:
        - 0-30 days
        - 31-60 days
        - 61-90 days
        - 91-180 days
        - 180+ days

    Use Cases:
        - Identify old stock
        - Inventory turnover analysis
        - Stock rotation planning
    """

    # permission_classes = [IsPharmacist]

    def get(self, request):
        """Get stock aging report"""
        try:
            today = timezone.now().date()

            stock_entries = MedicationStock.objects.select_related('medication').filter(
                is_active=True,
                medication__is_active=True
            ).annotate(
                current_stock=F('opening_quantity') + F('received_quantity') -
                              F('sold_quantity') - F('returned_quantity') -
                              F('damaged_quantity') + F('adjusted_quantity')
            ).filter(current_stock__gt=0)

            aging_categories = {
                '0-30 days': [],
                '31-60 days': [],
                '61-90 days': [],
                '91-180 days': [],
                '180+ days': []
            }

            for stock in stock_entries:
                age_days = (today - stock.received_date).days
                current_stock = stock.get_current_stock()
                stock_value = stock.purchase_price * current_stock

                stock_info = {
                    'medication_name': stock.medication.name,
                    'batch_number': stock.batch_number,
                    'current_stock': current_stock,
                    'stock_value': str(stock_value),
                    'received_date': stock.received_date,
                    'age_days': age_days,
                    'expiry_date': stock.expiry_date,
                }

                if age_days <= 30:
                    aging_categories['0-30 days'].append(stock_info)
                elif age_days <= 60:
                    aging_categories['31-60 days'].append(stock_info)
                elif age_days <= 90:
                    aging_categories['61-90 days'].append(stock_info)
                elif age_days <= 180:
                    aging_categories['91-180 days'].append(stock_info)
                else:
                    aging_categories['180+ days'].append(stock_info)

            # Calculate summary for each category
            summary = {}
            for category, items in aging_categories.items():
                total_value = sum([Decimal(item['stock_value']) for item in items])
                summary[category] = {
                    'count': len(items),
                    'total_value': str(total_value)
                }

            return Response({
                'status': 'success',
                'summary': summary,
                'aging_breakdown': aging_categories
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Stock aging report error: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Failed to generate stock aging report: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExpiryAlertReportView(APIView):
    """
    Expiry Alert Report API

    Purpose:
        List medications expiring soon or already expired.
        Critical for reducing medication wastage.

    Methods:
        GET: Get expiry alert report

    Query Parameters:
        alert_type (str, optional): 'expired', 'expiring_soon', 'all' (default: 'all')
        days_threshold (int, optional): Days to consider as "expiring soon" (default: 90)

    Response:
        Returns medications categorized by expiry status:
        - Already expired
        - Expiring within threshold
        - Days to expiry
        - Stock quantity
        - Stock value (potential loss)

    Use Cases:
        - Prevent medication wastage
        - Plan return to supplier
        - Discount pricing for near-expiry items
    """

    # permission_classes = [IsPharmacist]

    def get(self, request):
        """Get expiry alert report"""
        try:
            alert_type = request.query_params.get('alert_type', 'all')
            days_threshold = int(request.query_params.get('days_threshold', 90))

            today = timezone.now().date()
            threshold_date = today + timedelta(days=days_threshold)

            queryset = MedicationStock.objects.select_related('medication').filter(
                is_active=True,
                medication__is_active=True
            ).annotate(
                current_stock=F('opening_quantity') + F('received_quantity') -
                              F('sold_quantity') - F('returned_quantity') -
                              F('damaged_quantity') + F('adjusted_quantity')
            ).filter(current_stock__gt=0)

            expired_items = []
            expiring_soon_items = []

            for stock in queryset:
                current_stock = stock.get_current_stock()
                stock_value = stock.purchase_price * current_stock
                days_to_expiry = (stock.expiry_date - today).days

                item_info = {
                    'stock_id': stock.id,
                    'medication_name': stock.medication.name,
                    'dosage_form': stock.medication.dosage_form,
                    'strength': stock.medication.strength,
                    'batch_number': stock.batch_number,
                    'current_stock': current_stock,
                    'stock_value': str(stock_value),
                    'expiry_date': stock.expiry_date,
                    'days_to_expiry': days_to_expiry,
                    'supplier': stock.supplier,
                    'received_date': stock.received_date,
                }

                if stock.expiry_date < today:
                    expired_items.append(item_info)
                elif stock.expiry_date <= threshold_date:
                    expiring_soon_items.append(item_info)

            # Sort by days to expiry
            expired_items.sort(key=lambda x: x['days_to_expiry'])
            expiring_soon_items.sort(key=lambda x: x['days_to_expiry'])

            # Calculate totals
            total_expired_value = sum([Decimal(item['stock_value']) for item in expired_items])
            total_expiring_value = sum([Decimal(item['stock_value']) for item in expiring_soon_items])

            response_data = {
                'status': 'success',
                'alert_threshold_days': days_threshold,
            }

            if alert_type in ['expired', 'all']:
                response_data['expired'] = {
                    'count': len(expired_items),
                    'total_value': str(total_expired_value),
                    'items': expired_items
                }

            if alert_type in ['expiring_soon', 'all']:
                response_data['expiring_soon'] = {
                    'count': len(expiring_soon_items),
                    'total_value': str(total_expiring_value),
                    'items': expiring_soon_items
                }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Expiry alert report error: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Failed to generate expiry alert report: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MedicationExpiryDateFilterView(APIView):
    """
    Medication Expiry Date Range Filter API

    Purpose:
        Filter medications expiring within a specific date range.
        Returns only active stock that is not out of stock.

    Methods:
        GET: Get medications expiring between start_date and end_date

    Query Parameters:
        start_date (str, required): Start date (YYYY-MM-DD format)
        end_date (str, required): End date (YYYY-MM-DD format)
        page (int, optional): Page number (default: 1)
        page_size (int, optional): Items per page (default: 50, max: 200)

    Filters Applied:
        - is_active = True (active stock only)
        - quantity > 0 OR is_out_of_stock = False (in-stock only)
        - expiry_date between start_date and end_date

    Response:
        {
            "status": "success",
            "count": 25,
            "page": 1,
            "page_size": 50,
            "total_pages": 1,
            "date_range": {
                "start_date": "2025-01-01",
                "end_date": "2025-06-30"
            },
            "data": [
                {
                    "stock_id": 123,
                    "medication_id": 45,
                    "medication_name": "Paracetamol 500mg",
                    "dosage_form": "Tablet",
                    "strength": "500mg",
                    "batch_number": "BATCH-001",
                    "expiry_date": "2025-03-15",
                    "days_to_expiry": 87,
                    "quantity": 150,
                    "purchase_price": "6.00",
                    "mrp": "10.00",
                    "supplier": "ABC Pharma",
                    "received_date": "2024-12-01"
                }
            ]
        }

    Use Cases:
        - Generate expiry reports for specific periods
        - Plan stock clearance sales
        - Identify medications to return to supplier
        - Monthly/quarterly expiry tracking
    """

    def get(self, request):
        """
        Get medications expiring within date range

        Returns active, in-stock medications expiring between start_date and end_date
        """
        try:
            # Get and validate query parameters
            start_date_str = request.query_params.get('start_date')
            end_date_str = request.query_params.get('end_date')

            if not start_date_str or not end_date_str:
                return Response({
                    'status': 'error',
                    'message': 'Both start_date and end_date are required (format: YYYY-MM-DD)'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Parse dates
            try:
                from datetime import datetime
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD (e.g., 2025-01-31)'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate date range
            if start_date > end_date:
                return Response({
                    'status': 'error',
                    'message': 'start_date must be before or equal to end_date'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Pagination parameters
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 50)), 200)

            # Query medications expiring in the date range
            queryset = MedicationStock.objects.select_related('medication').filter(
                is_active=True,                    # Active stock only
                is_out_of_stock=False,              # Not out of stock
                quantity__gt=0,                      # Has quantity
                expiry_date__gte=start_date,        # Expires on or after start date
                expiry_date__lte=end_date,          # Expires on or before end date
                medication__is_active=True          # Active medication
            ).order_by('expiry_date', 'medication__name')

            # Get total count
            total_count = queryset.count()

            # Paginate
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            stock_items = queryset[start_idx:end_idx]

            # Build response data
            today = timezone.now().date()
            data = []

            for stock in stock_items:
                days_to_expiry = (stock.expiry_date - today).days

                data.append({
                    'stock_id': stock.id,
                    'medication_id': stock.medication.id,
                    'medication_name': stock.medication.name,
                    'dosage_form': stock.medication.dosage_form,
                    'strength': stock.medication.strength,
                    'batch_number': stock.batch_number,
                    'expiry_date': stock.expiry_date,
                    'days_to_expiry': days_to_expiry,
                    'quantity': stock.quantity,
                    'purchase_price': str(stock.purchase_price),
                    'selling_price': str(stock.selling_price),
                    'mrp': str(stock.mrp) if stock.mrp else None,
                    'supplier': stock.supplier,
                    'manufacturer': stock.manufacturer,
                    'received_date': stock.received_date,
                    'is_expired': stock.is_expired,
                    'is_near_expiry': stock.is_near_expiry
                })

            logger.info(f"Expiry date filter: {total_count} items found between {start_date} and {end_date}")

            return Response({
                'status': 'success',
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size,
                'date_range': {
                    'start_date': start_date_str,
                    'end_date': end_date_str
                },
                'data': data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Medication expiry filter error: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Failed to filter medications by expiry date: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LowStockAlertReportView(APIView):
    """
    Low Stock Alert Report API

    Purpose:
        Identify medications below reorder level.
        Helps prevent stockouts.

    Methods:
        GET: Get low stock alerts

    Query Parameters:
        threshold (int, optional): Minimum quantity threshold (default: 10)

    Response:
        Returns medications below threshold:
        - Current stock quantity
        - Reorder recommendation
        - Last restock date

    Use Cases:
        - Prevent stockouts
        - Automated purchase requisition
        - Inventory replenishment planning
    """

    # permission_classes = [IsPharmacist]

    def get(self, request):
        """Get low stock alert report"""
        try:
            threshold = int(request.query_params.get('threshold', 10))

            low_stock_items = MedicationStock.objects.select_related('medication').filter(
                is_active=True,
                medication__is_active=True
            ).annotate(
                current_stock=F('opening_quantity') + F('received_quantity') -
                              F('sold_quantity') - F('returned_quantity') -
                              F('damaged_quantity') + F('adjusted_quantity')
            ).filter(
                current_stock__lte=threshold,
                current_stock__gt=0
            ).order_by('current_stock')

            result = []
            for stock in low_stock_items:
                current_stock = stock.get_current_stock()

                # Calculate suggested reorder quantity based on average sales
                avg_monthly_sales = stock.sold_quantity / max(1, (timezone.now().date() - stock.received_date).days / 30)
                suggested_reorder = max(threshold * 2, int(avg_monthly_sales * 2))  # 2 months supply

                result.append({
                    'stock_id': stock.id,
                    'medication_id': stock.medication.id,
                    'medication_name': stock.medication.name,
                    'dosage_form': stock.medication.dosage_form,
                    'strength': stock.medication.strength,
                    'current_stock': current_stock,
                    'threshold': threshold,
                    'supplier': stock.supplier,
                    'last_received_date': stock.received_date,
                    'total_sold': stock.sold_quantity,
                    'suggested_reorder_quantity': suggested_reorder,
                    'is_out_of_stock': current_stock == 0,
                    'alert_level': 'critical' if current_stock <= threshold / 2 else 'warning'
                })

            return Response({
                'status': 'success',
                'threshold': threshold,
                'count': len(result),
                'low_stock_items': result
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Low stock alert report error: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Failed to generate low stock alert report: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# MEDICINE RETURNS MODULE
# ============================================================================

class PatientBillDetailView(APIView):
    """
    Get patient bill details for initiating a return
    """
    def get(self, request, bill_number):
        """Get bill details with dispensed medicines"""
        try:
            # Find bill
            bill = PatientBill.objects.select_related(
                'appointment__patient',
                'consultation'
            ).get(bill_number=bill_number)

            # Check if bill is paid
            if bill.payment_status != 'PAID':
                return Response({
                    'status': 'error',
                    'message': 'Can only return medicines from paid bills'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get medicine items from JSON
            medicine_items = bill.medicine_items or []

            # Get dispensed medicines for this consultation
            dispensed_medicines = MedicationDispense.objects.filter(
                prescribed_medicine__consultation=bill.consultation
            ).select_related(
                'prescribed_medicine__medicine',
                'stock_entry'
            )

            # Build returnable items list
            returnable_items = []
            for dispense in dispensed_medicines:
                medication = dispense.prescribed_medicine.medicine
                returnable_items.append({
                    'medication_id': medication.id,
                    'medication_name': f"{medication.name} {medication.strength}",
                    'dosage_form': medication.dosage_form,
                    'stock_entry_id': dispense.stock_entry.id,
                    'batch_number': dispense.stock_entry.batch_number,
                    'expiry_date': dispense.stock_entry.expiry_date,
                    'quantity_dispensed': dispense.quantity_dispensed,
                    'unit_price': float(dispense.stock_entry.selling_price),
                })

            # Get existing returns for this bill
            existing_returns = PatientMedicineReturn.objects.filter(
                patient_bill=bill
            ).prefetch_related('items')

            total_returned = {}
            for ret in existing_returns:
                for item in ret.items.all():
                    key = (item.medication.id, item.stock_entry.id)
                    total_returned[key] = total_returned.get(key, 0) + item.quantity_returned

            # Add returned quantities to items
            for item in returnable_items:
                key = (item['medication_id'], item['stock_entry_id'])
                item['quantity_already_returned'] = total_returned.get(key, 0)
                item['quantity_available_for_return'] = item['quantity_dispensed'] - item['quantity_already_returned']

            return Response({
                'status': 'success',
                'data': {
                    'bill_number': bill.bill_number,
                    'bill_date': bill.bill_date,
                    'patient_id': bill.appointment.patient.id,
                    'patient_name': bill.patient_name,
                    'total_bill_amount': float(bill.total_bill_amount),
                    'payment_type': bill.payment_type,
                    'returnable_items': returnable_items,
                    'existing_returns_count': existing_returns.count()
                }
            })

        except PatientBill.DoesNotExist:
            return Response({
                'status': 'error',
                'message': f'Bill {bill_number} not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Error fetching bill details: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch bill details'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MedicineReturnCreateView(APIView):
    """
    Create a new medicine return and process refund
    """
    def post(self, request):
        """Create medicine return with items"""
        try:
            serializer = MedicineReturnCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Create the return
            medicine_return = serializer.save()

            # Process refund immediately (simplified workflow)
            from django.utils import timezone

            medicine_return.is_refunded = True
            medicine_return.processed_by = request.user
            medicine_return.processed_date = timezone.now()
            medicine_return.save()

            # Adjust stock automatically
            medicine_return.process_stock_adjustment()

            # Return detailed response
            response_serializer = MedicineReturnSerializer(medicine_return)

            return Response({
                'status': 'success',
                'message': f'Medicine return {medicine_return.return_number} processed successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)

        except serializers.ValidationError as e:
            logger.warning(f"Medicine return validation failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Validation failed',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Medicine return creation failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to process medicine return'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MedicineReturnListView(APIView):
    """
    List all medicine returns with filtering and pagination
    """
    def get(self, request):
        """List medicine returns"""
        try:
            # Base queryset
            queryset = PatientMedicineReturn.objects.select_related(
                'patient',
                'patient_bill',
                'processed_by'
            ).prefetch_related('items')

            # Filters
            is_refunded = request.query_params.get('is_refunded')
            patient_id = request.query_params.get('patient_id')
            bill_number = request.query_params.get('bill_number')
            return_number = request.query_params.get('return_number')
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')

            if is_refunded is not None:
                queryset = queryset.filter(is_refunded=is_refunded.lower() == 'true')

            if patient_id:
                queryset = queryset.filter(patient_id=patient_id)

            if bill_number:
                queryset = queryset.filter(patient_bill__bill_number__icontains=bill_number)

            if return_number:
                queryset = queryset.filter(return_number__icontains=return_number)

            if date_from:
                queryset = queryset.filter(return_date__gte=date_from)

            if date_to:
                queryset = queryset.filter(return_date__lte=date_to)

            # Ordering
            queryset = queryset.order_by('-return_date', '-id')

            # Pagination
            from django.core.paginator import Paginator
            page = request.query_params.get('page', 1)
            page_size = request.query_params.get('page_size', 20)

            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)

            serializer = MedicineReturnSerializer(page_obj.object_list, many=True)

            return Response({
                'status': 'success',
                'data': {
                    'count': paginator.count,
                    'page': int(page),
                    'page_size': int(page_size),
                    'total_pages': paginator.num_pages,
                    'results': serializer.data
                }
            })

        except Exception as e:
            logger.error(f"Error listing medicine returns: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to list medicine returns'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MedicineReturnDetailView(APIView):
    """
    Get detailed information about a specific medicine return
    """
    def get(self, request, return_id):
        """Get medicine return details"""
        try:
            medicine_return = PatientMedicineReturn.objects.select_related(
                'patient',
                'patient_bill',
                'processed_by'
            ).prefetch_related(
                'items__medication',
                'items__stock_entry'
            ).get(id=return_id)

            serializer = MedicineReturnSerializer(medicine_return)

            return Response({
                'status': 'success',
                'data': serializer.data
            })

        except PatientMedicineReturn.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Medicine return not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Error fetching medicine return: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch medicine return details'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MedicineReturnReportView(APIView):
    """
    Generate reports and statistics for medicine returns
    """
    def get(self, request):
        """Get medicine return statistics"""
        try:
            from django.db.models import Sum, Count, Avg
            from datetime import datetime, timedelta

            # Date range
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')

            queryset = PatientMedicineReturn.objects.all()

            if date_from:
                queryset = queryset.filter(return_date__gte=date_from)
            if date_to:
                queryset = queryset.filter(return_date__lte=date_to)

            # Overall statistics
            total_returns = queryset.count()
            total_refunded = queryset.filter(is_refunded=True).count()
            total_refund_amount = queryset.filter(
                is_refunded=True
            ).aggregate(
                total=Sum('total_refund_amount')
            )['total'] or 0

            # Most returned medications
            from django.db.models import Q
            most_returned = PatientMedicineReturnItem.objects.filter(
                patient_return__in=queryset
            ).values(
                'medication__name',
                'medication__strength',
                'medication__dosage_form'
            ).annotate(
                total_quantity=Sum('quantity_returned'),
                return_count=Count('id')
            ).order_by('-total_quantity')[:10]

            # Returns by condition
            condition_stats = PatientMedicineReturnItem.objects.filter(
                patient_return__in=queryset
            ).values('condition').annotate(
                count=Count('id'),
                total_amount=Sum('refund_amount')
            )

            # Returns by refund method
            refund_method_stats = queryset.filter(
                is_refunded=True
            ).values('refund_method').annotate(
                count=Count('id'),
                total_amount=Sum('total_refund_amount')
            )

            return Response({
                'status': 'success',
                'data': {
                    'summary': {
                        'total_returns': total_returns,
                        'total_refunded': total_refunded,
                        'total_refund_amount': float(total_refund_amount),
                        'pending_returns': total_returns - total_refunded
                    },
                    'most_returned_medications': list(most_returned),
                    'by_condition': list(condition_stats),
                    'by_refund_method': list(refund_method_stats)
                }
            })

        except Exception as e:
            logger.error(f"Error generating medicine return report: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to generate report'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# LAB TEST ORDER MANAGEMENT (External Lab Integration)
# ============================================================================
# Author: Athul Gopan
# Purpose: Manage lab test orders sent to external laboratories
#          Support partial payments, PDF result uploads, and order tracking
# ============================================================================

class LabTestOrderView(APIView):
    """
    Lab Test Order Management API

    Purpose:
        Manage lab test orders for external laboratories.
        Supports walk-in and appointment-based patients.
        Handles partial payment workflow.

    Endpoints:
        GET    /api/pharmacy/lab-test-orders/              - List all orders (with filters)
        POST   /api/pharmacy/lab-test-orders/              - Create new order
        GET    /api/pharmacy/lab-test-orders/<order_id>/   - Get order details
        PUT    /api/pharmacy/lab-test-orders/<order_id>/   - Update order
        PATCH  /api/pharmacy/lab-test-orders/<order_id>/   - Partial update
        DELETE /api/pharmacy/lab-test-orders/<order_id>/   - Soft delete order

    Query Parameters (GET list):
        - status: Filter by order status (ORDERED, SENT, RECEIVED, etc.)
        - payment_status: Filter by payment status (PAID, UNPAID, PARTIALLY_PAID)
        - patient_id: Filter by patient ID
        - from_date: Filter orders from date (YYYY-MM-DD)
        - to_date: Filter orders to date (YYYY-MM-DD)
        - external_lab: Filter by external lab name

    Features:
        - Auto-generate order numbers
        - Support walk-in patients (no appointment)
        - Partial payment tracking
        - Status management
        - Date range filtering
        - Patient history

    Workflow:
        1. Create order with selected tests
        2. Collect payment (full/partial)
        3. Mark as SENT when sent to lab
        4. Upload PDF when results received (status: RECEIVED)
        5. Mark as COMPLETED when delivered to patient

    Related Models:
        - LabTestOrder
        - LabPaymentTransaction
        - LabTestResult
    """
    # permission_classes = [IsAuthenticated]

    def get(self, request, order_id=None):
        """
        GET: Retrieve lab test orders

        Parameters:
            order_id (int, optional): Specific order ID for detail view

        Returns:
            - List of orders (if no order_id)
            - Single order details (if order_id provided)
        """
        try:
            # Detail view - single order
            if order_id:
                try:
                    order = LabTestOrder.objects.select_related(
                        'patient', 'appointment', 'created_by'
                    ).prefetch_related(
                        'lab_departments',
                        'payments__received_by',
                        'results__uploaded_by'
                    ).get(id=order_id, is_active=True)

                    serializer = LabTestOrderSerializer(order, context={'request': request})
                    return Response({
                        'status': 'success',
                        'data': serializer.data
                    }, status=status.HTTP_200_OK)

                except LabTestOrder.DoesNotExist:
                    return Response({
                        'status': 'error',
                        'message': 'Lab test order not found'
                    }, status=status.HTTP_404_NOT_FOUND)

            # List view - with filters
            orders = LabTestOrder.objects.select_related(
                'patient', 'appointment'
            ).prefetch_related(
                'lab_departments'
            ).filter(is_active=True)

            # Apply filters
            order_status = request.query_params.get('status')
            if order_status:
                orders = orders.filter(status=order_status)

            payment_status = request.query_params.get('payment_status')
            if payment_status:
                orders = orders.filter(payment_status=payment_status)

            patient_id = request.query_params.get('patient_id')
            if patient_id:
                orders = orders.filter(patient_id=patient_id)

            from_date = request.query_params.get('from_date')
            if from_date:
                orders = orders.filter(date_ordered__gte=from_date)

            to_date = request.query_params.get('to_date')
            if to_date:
                orders = orders.filter(date_ordered__lte=to_date)

            external_lab = request.query_params.get('external_lab')
            if external_lab:
                orders = orders.filter(external_lab_name__icontains=external_lab)

            # Order by latest first
            orders = orders.order_by('-date_ordered', '-created_on')

            # Serialize
            serializer = LabTestOrderListSerializer(orders, many=True, context={'request': request})

            return Response({
                'status': 'success',
                'count': orders.count(),
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving lab test orders: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @transaction.atomic
    def post(self, request):
        """
        POST: Create new lab test order

        Request Body:
            {
                "patient": 1,
                "appointment": null,  # Optional, null for walk-ins
                "selected_tests": [
                    {"id": 1, "name": "CBC", "category": "Hematology", "price": 500},
                    {"id": 2, "name": "Blood Sugar", "category": "Biochemistry", "price": 200}
                ],
                "total_amount": 700,
                "paid_amount": 300,  # Partial payment
                "discount": 0,
                "external_lab_name": "Path Lab",
                "special_instructions": "Fasting required"
            }

        Returns:
            - Created order details with auto-generated order number
        """
        try:
            serializer = LabTestOrderSerializer(data=request.data, context={'request': request})

            if serializer.is_valid():
                order = serializer.save()

                # Create initial payment transaction if paid_amount > 0
                if order.paid_amount > 0:
                    LabPaymentTransaction.objects.create(
                        lab_order=order,
                        amount=order.paid_amount,
                        payment_type=request.data.get('payment_type', 'CASH'),
                        received_by=request.user,
                        notes="Initial payment"
                    )

                # Refresh to get nested data
                order.refresh_from_db()
                response_serializer = LabTestOrderSerializer(order, context={'request': request})

                return Response({
                    'status': 'success',
                    'message': 'Lab test order created successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_201_CREATED)

            return Response({
                'status': 'error',
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error creating lab test order: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @transaction.atomic
    def put(self, request, order_id):
        """
        PUT: Update lab test order (full update)

        Parameters:
            order_id (int): Order ID to update

        Note:
            Use PATCH for partial updates (e.g., status change only)
        """
        try:
            order = LabTestOrder.objects.get(id=order_id, is_active=True)

            serializer = LabTestOrderSerializer(
                order,
                data=request.data,
                context={'request': request},
                partial=False
            )

            if serializer.is_valid():
                # Set updated_by
                if hasattr(request, 'user'):
                    order.updated_by = request.user

                updated_order = serializer.save()

                return Response({
                    'status': 'success',
                    'message': 'Lab test order updated successfully',
                    'data': LabTestOrderSerializer(updated_order, context={'request': request}).data
                }, status=status.HTTP_200_OK)

            return Response({
                'status': 'error',
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except LabTestOrder.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Lab test order not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Error updating lab test order: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @transaction.atomic
    def patch(self, request, order_id):
        """
        PATCH: Partial update lab test order

        Common use cases:
            - Update status: {"status": "SENT", "date_sent": "2025-12-14"}
            - Update payment: {"paid_amount": 500}
            - Add external reference: {"external_reference_number": "EXT123"}

        Parameters:
            order_id (int): Order ID to update
        """
        try:
            order = LabTestOrder.objects.get(id=order_id, is_active=True)

            serializer = LabTestOrderSerializer(
                order,
                data=request.data,
                context={'request': request},
                partial=True
            )

            if serializer.is_valid():
                # Set updated_by
                if hasattr(request, 'user'):
                    order.updated_by = request.user

                updated_order = serializer.save()

                return Response({
                    'status': 'success',
                    'message': 'Lab test order updated successfully',
                    'data': LabTestOrderSerializer(updated_order, context={'request': request}).data
                }, status=status.HTTP_200_OK)

            return Response({
                'status': 'error',
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except LabTestOrder.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Lab test order not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Error updating lab test order: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @transaction.atomic
    def delete(self, request, order_id):
        """
        DELETE: Soft delete lab test order

        Parameters:
            order_id (int): Order ID to delete

        Note:
            Performs soft delete (sets is_active=False)
            Only ORDERED or CANCELLED orders can be deleted
        """
        try:
            order = LabTestOrder.objects.get(id=order_id, is_active=True)

            # Validate deletion
            if order.status not in ['ORDERED', 'CANCELLED']:
                return Response({
                    'status': 'error',
                    'message': f'Cannot delete order with status: {order.status}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Soft delete
            order.is_active = False
            order.updated_by = request.user if hasattr(request, 'user') else None
            order.save()

            return Response({
                'status': 'success',
                'message': 'Lab test order deleted successfully'
            }, status=status.HTTP_200_OK)

        except LabTestOrder.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Lab test order not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Error deleting lab test order: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LabPaymentView(APIView):
    """
    Lab Payment Transaction API

    Purpose:
        Record additional payments for lab test orders.
        Supports partial payment workflow.

    Endpoints:
        POST /api/pharmacy/lab-test-orders/<order_id>/payment/ - Add payment

    Features:
        - Record partial payments
        - Auto-update order payment status
        - Generate transaction IDs
        - Track payment method
        - Receipt generation support

    Workflow:
        1. Patient makes payment (full/partial)
        2. Staff records payment transaction
        3. System auto-updates paid_amount and balance
        4. System auto-updates payment_status
    """
    # permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_id):
        """
        POST: Add payment transaction to lab order

        Request Body:
            {
                "amount": 200,
                "payment_type": "CASH",  # CASH, CARD, UPI, etc.
                "receipt_number": "RCP-001",  # Optional
                "notes": "Second payment"  # Optional
            }

        Returns:
            - Updated order with new payment included
        """
        try:
            # Get lab order
            order = LabTestOrder.objects.select_related('patient').get(
                id=order_id,
                is_active=True
            )

            # Validate amount
            amount = request.data.get('amount')
            if not amount or float(amount) <= 0:
                return Response({
                    'status': 'error',
                    'message': 'Invalid payment amount'
                }, status=status.HTTP_400_BAD_REQUEST)

            amount = float(amount)

            # Check if payment exceeds balance
            if amount > order.balance_amount:
                return Response({
                    'status': 'error',
                    'message': f'Payment amount (₹{amount}) exceeds balance (₹{order.balance_amount})'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create payment transaction
            payment = LabPaymentTransaction.objects.create(
                lab_order=order,
                amount=amount,
                payment_type=request.data.get('payment_type', 'CASH'),
                received_by=request.user if hasattr(request, 'user') else None,
                receipt_number=request.data.get('receipt_number'),
                notes=request.data.get('notes', ''),
                created_by=request.user if hasattr(request, 'user') else None
            )

            # Update order payment amounts
            order.paid_amount += amount
            order.balance_amount = order.total_amount - order.paid_amount - order.discount

            # Update payment status
            if order.balance_amount <= 0:
                order.payment_status = 'PAID'
            elif order.paid_amount > 0:
                order.payment_status = 'PARTIALLY_PAID'

            order.updated_by = request.user if hasattr(request, 'user') else None
            order.save()

            # Refresh and serialize
            order.refresh_from_db()
            order_serializer = LabTestOrderSerializer(order, context={'request': request})
            payment_serializer = LabPaymentTransactionSerializer(payment)

            return Response({
                'status': 'success',
                'message': 'Payment recorded successfully',
                'payment': payment_serializer.data,
                'order': order_serializer.data
            }, status=status.HTTP_201_CREATED)

        except LabTestOrder.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Lab test order not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Error recording payment: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LabResultUploadView(APIView):
    """
    Lab Test Result Upload API

    Purpose:
        Upload PDF reports received from external laboratories.
        Automatically updates order status to RECEIVED.

    Endpoints:
        POST /api/pharmacy/lab-test-orders/<order_id>/upload-result/ - Upload PDF

    Features:
        - PDF file validation
        - Auto-extract file metadata
        - Update order status
        - Track upload user and timestamp
        - Link result to patient and order

    File Storage:
        - Location: media/lab_reports/YYYY/MM/
        - Format: PDF only
        - Max size: 10MB

    Workflow:
        1. External lab sends PDF report
        2. Staff uploads PDF via this API
        3. System validates PDF
        4. System stores PDF with metadata
        5. Order status updated to RECEIVED
        6. date_received set to current date
    """
    # permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_id):
        """
        POST: Upload PDF result for lab order

        Request Body (multipart/form-data):
            - report_pdf: PDF file (required)
            - report_date: Date on report (YYYY-MM-DD) (required)
            - notes: Additional notes (optional)

        Returns:
            - Uploaded result details
            - Updated order status
        """
        try:
            # Get lab order
            order = LabTestOrder.objects.select_related('patient').get(
                id=order_id,
                is_active=True
            )

            # Validate order status
            if order.status not in ['SENT', 'RECEIVED' ,'ORDERED']:
                return Response({
                    'status': 'error',
                    'message': f'Cannot upload result for order with status: {order.status}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Prepare data
            data = {
                'lab_order': order.id,
                'patient': order.patient.id,
                'report_pdf': request.FILES.get('report_pdf'),
                'report_date': request.data.get('report_date'),
                'uploaded_by': request.user.id if hasattr(request, 'user') else None,
                'notes': request.data.get('notes', '')
            }

            # Validate and create result
            serializer = LabTestResultSerializer(data=data, context={'request': request})

            if serializer.is_valid():
                result = serializer.save(
                    created_by=request.user if hasattr(request, 'user') else None
                )

                # Update order status
                order.status = 'RECEIVED'
                order.date_received = result.report_date
                order.updated_by = request.user if hasattr(request, 'user') else None
                order.save()

                # Refresh order
                order.refresh_from_db()
                order_serializer = LabTestOrderSerializer(order, context={'request': request})

                return Response({
                    'status': 'success',
                    'message': 'Lab result uploaded successfully',
                    'result': serializer.data,
                    'order': order_serializer.data
                }, status=status.HTTP_201_CREATED)

            return Response({
                'status': 'error',
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except LabTestOrder.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Lab test order not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Error uploading lab result: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientLabResultsView(APIView):
    """
    Patient Lab Results API

    Purpose:
        Retrieve all lab test results for a specific patient.
        Shows complete history of lab reports with PDF links.

    Endpoint:
        GET /api/pharmacy/patients/<patient_id>/lab-results/

    Query Parameters:
        - from_date: Filter results from date (YYYY-MM-DD)
        - to_date: Filter results to date (YYYY-MM-DD)
        - order_by: Sort order (default: -report_date)

    Response:
        {
            "status": "success",
            "patient_id": 123,
            "patient_name": "John Doe",
            "count": 5,
            "results": [
                {
                    "id": 1,
                    "order_number": "LAB-2025-0001",
                    "report_date": "2025-12-15",
                    "report_pdf_url": "http://...",
                    "file_name": "CBC_Report.pdf",
                    "file_size": 1024000,
                    "uploaded_by_name": "lab_staff",
                    "uploaded_on": "2025-12-15T10:30:00Z",
                    "notes": "All parameters normal",
                    "selected_tests": [...]
                }
            ]
        }
    """
    # permission_classes = [IsAuthenticated]

    def get(self, request, patient_id):
        """
        GET: Retrieve all lab results for a patient

        Parameters:
            patient_id (int): Patient ID
        """
        try:
            # Validate patient exists
            try:
                patient = PatientRegistration.objects.get(id=patient_id, is_active=True)
            except PatientRegistration.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'Patient not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Get all lab results for patient
            results = LabTestResult.objects.select_related(
                'lab_order', 'uploaded_by'
            ).filter(
                patient_id=patient_id,
                is_active=True
            )

            # Apply date filters if provided
            from_date = request.query_params.get('from_date')
            if from_date:
                results = results.filter(report_date__gte=from_date)

            to_date = request.query_params.get('to_date')
            if to_date:
                results = results.filter(report_date__lte=to_date)

            # Order by report date (latest first)
            order_by = request.query_params.get('order_by', '-report_date')
            results = results.order_by(order_by, '-uploaded_on')

            # Serialize results
            serializer = LabTestResultSerializer(results, many=True, context={'request': request})

            # Prepare response with patient info
            return Response({
                'status': 'success',
                'patient_id': patient.id,
                'patient_name': f"{patient.first_name} {patient.last_name}",
                'count': results.count(),
                'results': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving patient lab results: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LabTestListView(APIView):
    """
    Lab Test List API (Lightweight)

    Purpose:
        Returns simple list of available lab tests for order creation.
        Only returns id, name, and rate - no nested data.

    Endpoint:
        GET /api/pharmacy/lab-tests/

    Query Parameters:
        - is_active: Filter active tests only (default: true)
        - search: Search by test name (case-insensitive)

    Response:
        {
            "status": "success",
            "count": 5,
            "data": [
                {
                    "id": 1,
                    "name": "Hematology (CBC)",
                    "rate": 500
                },
                {
                    "id": 2,
                    "name": "Biochemistry (Blood Sugar)",
                    "rate": 150
                }
            ]
        }

    Use Case:
        - Lab test selection dropdown in order creation form
        - Quick test lookup
        - Minimal data transfer for mobile apps

    Performance:
        - No nested queries
        - No prefetch/select_related needed
        - Fast response time
    """
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get lightweight list of lab tests"""
        try:
            # Get all lab departments (which represent individual tests)
            tests = LabDepartment.objects.all()

            # Filter active only (default)
            is_active = request.query_params.get('is_active', 'true').lower()
            if is_active == 'true':
                tests = tests.filter(is_active=True)

            # Search filter
            search = request.query_params.get('search')
            if search:
                tests = tests.filter(name__icontains=search)

            # Order by name
            tests = tests.order_by('name')

            # Serialize with lightweight serializer
            serializer = LabDepartmentSimpleSerializer(tests, many=True)

            return Response({
                'status': 'success',
                'count': tests.count(),
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching lab tests: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# END OF PHARMACY MODULE VIEWS
# ============================================================================


# ============================================================================
# STOCK ALLOCATION & TRANSFER VIEWS
# ============================================================================

class StockAllocationView(APIView):
    """
    Stock Allocation API

    Purpose:
        Allocate medication stock to different departments
        (Pharmacy, Home Care, Casualty)

    Methods:
        POST: Allocate stock to departments

    Request Body:
        {
            "stock_entry": 8,
            "pharmacy_quantity": 100,
            "home_care_quantity": 600,
            "casualty_quantity": 300
        }

    Business Logic:
        - Total allocation cannot exceed available stock
        - Updates department quantities
        - Previous allocations are replaced (not added)
    """

    def post(self, request):
        """Allocate stock to departments"""
        try:
            serializer = StockAllocationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            stock = serializer.validated_data['stock']

            # Update department allocations
            stock.pharmacy_quantity = serializer.validated_data.get('pharmacy_quantity', 0)
            stock.home_care_quantity = serializer.validated_data.get('home_care_quantity', 0)
            stock.casualty_quantity = serializer.validated_data.get('casualty_quantity', 0)
            stock.save()

            # Return updated stock details
            response_serializer = MedicationStockAllocationSerializer(stock)

            return Response({
                'status': 'success',
                'message': 'Stock allocated successfully',
                'data': response_serializer.data
            }, status=status.HTTP_200_OK)

        except serializers.ValidationError as e:
            return Response({
                'status': 'error',
                'message': 'Validation failed',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Stock allocation failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to allocate stock'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StockTransferCreateView(APIView):
    """
    Stock Transfer Create API

    Purpose:
        Transfer stock between departments
        (Borrow from one department to another)

    Methods:
        POST: Create and execute stock transfer

    Request Body:
        {
            "stock_entry": 8,
            "from_department": "CASUALTY",
            "to_department": "HOME_CARE",
            "quantity_transferred": 50,
            "reason": "Home care stock low"
        }

    Business Logic:
        - Validates source department has sufficient quantity
        - Cannot transfer to same department
        - Automatically processes transfer (updates quantities)
        - Creates audit trail record
    """

    def post(self, request):
        """Create and execute stock transfer"""
        try:
            serializer = StockTransferCreateSerializer(
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)

            # Create and process transfer
            transfer = serializer.save()

            # Return transfer details
            response_serializer = StockTransferSerializer(transfer)

            return Response({
                'status': 'success',
                'message': f'Stock transferred successfully from {transfer.from_department} to {transfer.to_department}',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)

        except serializers.ValidationError as e:
            return Response({
                'status': 'error',
                'message': 'Validation failed',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Stock transfer failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to process stock transfer'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StockTransferListView(APIView):
    """
    Stock Transfer List API

    Purpose:
        Retrieve list of all stock transfers with filtering

    Methods:
        GET: List stock transfers

    Query Parameters:
        - stock_entry (int): Filter by stock entry ID
        - from_department (str): Filter by source department
        - to_department (str): Filter by destination department
        - date_from (date): Filter from this date
        - date_to (date): Filter to this date
        - status (str): Filter by status
        - page (int): Page number
        - page_size (int): Items per page

    Response:
        Paginated list of transfers with details
    """

    def get(self, request):
        """List stock transfers"""
        try:
            # Base queryset
            queryset = StockTransfer.objects.select_related(
                'stock_entry',
                'stock_entry__medication',
                'transferred_by'
            ).filter(is_active=True)

            # Filters
            stock_entry = request.query_params.get('stock_entry')
            from_dept = request.query_params.get('from_department')
            to_dept = request.query_params.get('to_department')
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')
            transfer_status = request.query_params.get('status')

            if stock_entry:
                queryset = queryset.filter(stock_entry_id=stock_entry)

            if from_dept:
                queryset = queryset.filter(from_department=from_dept)

            if to_dept:
                queryset = queryset.filter(to_department=to_dept)

            if date_from:
                queryset = queryset.filter(transfer_date__gte=date_from)

            if date_to:
                queryset = queryset.filter(transfer_date__lte=date_to)

            if transfer_status:
                queryset = queryset.filter(status=transfer_status)

            # Ordering
            queryset = queryset.order_by('-transfer_date')

            # Pagination
            from django.core.paginator import Paginator
            page = request.query_params.get('page', 1)
            page_size = request.query_params.get('page_size', 20)

            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)

            # Serialize
            serializer = StockTransferSerializer(page_obj, many=True)

            return Response({
                'status': 'success',
                'count': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'page_size': int(page_size),
                'results': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to fetch stock transfers: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch stock transfers'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StockAllocationStatusView(APIView):
    """
    Stock Allocation Status API

    Purpose:
        Get allocation status for all stock entries or specific medication

    Methods:
        GET: Get allocation status

    Query Parameters:
        - medication (int): Filter by medication ID
        - department (str): Show only this department's allocations

    Response:
        List of stock entries with allocation details
    """

    def get(self, request):
        """Get stock allocation status"""
        try:
            # Base queryset
            queryset = MedicationStock.objects.select_related(
                'medication'
            ).filter(is_active=True, quantity__gt=0)

            # Filters
            medication_id = request.query_params.get('medication')
            department = request.query_params.get('department')

            if medication_id:
                queryset = queryset.filter(medication_id=medication_id)

            # Serialize
            serializer = MedicationStockAllocationSerializer(queryset, many=True)

            # If department filter specified, add summary
            if department:
                total_allocated = sum(
                    getattr(stock, f'{department.lower()}_quantity', 0)
                    for stock in queryset
                )
                return Response({
                    'status': 'success',
                    'department': department,
                    'total_allocated': total_allocated,
                    'stocks': serializer.data
                }, status=status.HTTP_200_OK)

            return Response({
                'status': 'success',
                'count': queryset.count(),
                'results': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to fetch allocation status: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch allocation status'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
