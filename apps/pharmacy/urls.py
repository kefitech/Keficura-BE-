from django.urls import path
from .views import *

urlpatterns = [
    # ============================================================================
    # SUPPLIER MANAGEMENT URLs
    # ============================================================================
    path('suppliers/', SupplierView.as_view(), name='supplier-list-create'),
    path('suppliers/<int:supplier_id>/', SupplierView.as_view(), name='supplier-detail'),
    path('suppliers/search/', SupplierSearchView.as_view(), name='supplier-search'),

    # ============================================================================
    # PURCHASE ORDER URLs
    # ============================================================================
    path('purchase-orders/', PurchaseOrderView.as_view(), name='purchase-order-list-create'),
    path('purchase-orders/<int:po_id>/', PurchaseOrderView.as_view(), name='purchase-order-detail'),
    path('purchase-orders/<int:po_id>/approve/', PurchaseOrderApproveView.as_view(), name='purchase-order-approve'),

    # ============================================================================
    # PURCHASE ENTRY (GRN) URLs
    # ============================================================================
    path('purchase-entries/', PurchaseEntryView.as_view(), name='purchase-entry-list-create'),
    path('purchase-entries/bulk-details/', PurchaseEntryBulkDetailsView.as_view(), name='purchase-entry-bulk-details'),
    path('purchase-entries/bulk-approve/', PurchaseEntryBulkApproveView.as_view(), name='purchase-entry-bulk-approve'),
    path('purchase-entries/<int:grn_id>/', PurchaseEntryView.as_view(), name='purchase-entry-detail'),
    path('purchase-entries/<int:grn_id>/approve/', PurchaseEntryApproveView.as_view(), name='purchase-entry-approve'),
    path('purchase-entries/<int:grn_id>/items/', PurchaseEntryItemsView.as_view(), name='purchase-entry-items'),

    # ============================================================================
    # SUPPLIER RETURN (PURCHASE RETURN) URLs
    # ============================================================================
    path('supplier-returns/', SupplierReturnView.as_view(), name='supplier-return-list-create'),
    path('supplier-returns/<int:return_id>/', SupplierReturnView.as_view(), name='supplier-return-detail'),
    path('supplier-returns/<int:return_id>/approve/', SupplierReturnApproveView.as_view(), name='supplier-return-approve'),
    path('supplier-returns/<int:return_id>/items/', SupplierReturnItemsView.as_view(), name='supplier-return-items'),

    # ============================================================================
    # PHARMACIST & PROFILE URLs
    # ============================================================================
    path('pharmacist_profile/', PharmacistProfileView.as_view(), name='pharmacist_profile'),

    # ============================================================================
    # MEDICATION MANAGEMENT URLs
    # ============================================================================
    path('medications/', MedicationView.as_view(), name='medications'),
    path('pharma-available-meds/', MedicationListView.as_view(), name='pharma-available-meds'),
    path('dispensable-meds/', DispensableMedicationView.as_view(), name='dispensable-meds'),
    path('doctor-med/', MedicationList.as_view(), name='doctor-med'),
    path('stock/', MedicationStockView.as_view(), name='medication-stock'),

    # ============================================================================
    # CONSULTATION & PRESCRIPTION URLs
    # ============================================================================
    path('consultations/', DoctorConsultationView.as_view(), name='consultation-list-create'),
    path('pharma-consultation/', PharmaConsultationView.as_view(), name='pharma-consultation'),
    path('doctor-prescribed-medicine/', PharmaPrescribedMedicineView.as_view(), name='pharma-prescribed-medicine'),
    path('patient-history/<str:patient_id>/', PatientHistoryView.as_view(), name='patient-history'),

    # ============================================================================
    # MEDICATION DISPENSING URLs
    # ============================================================================
    path('dispense/', DispenseView.as_view(), name='dispense-medication'),
    path('pharma-medicine-dispense/', PrescribedMedicationDispense.as_view(), name='pharma-medicine-dispense'),

    # ============================================================================
    # BILLING & PAYMENT URLs
    # ============================================================================
    path('bill-preview/', FinalBillPreviewView.as_view(), name='bill-preview'),
    path('bill-consultation/', BillingConsultationView.as_view(), name='bill-consultation'),
    path('save-bill/', Generated_bill_save.as_view(), name='save-bill'),
    path('bill-history/', PaymentHistoryView.as_view(), name='bill-history'),
    path('pharma-bill/', Pharmacy_Items.as_view(), name='pharma-bill'),

    # ============================================================================
    # LABORATORY MANAGEMENT URLs
    # ============================================================================

    # Lab Department URLs
    path('lab-department/', DepartmentCreateView.as_view(), name='lab-department-list-create'),
    path('lab-department/<int:department_id>/', DepartmentCreateView.as_view(), name='lab-department-detail'),

    # Lab Test Category URLs
    path('lab-test-category/', TestCategoryCreateView.as_view(), name='lab-test-category-list-create'),
    path('lab-test-category/<int:category_id>/', TestCategoryCreateView.as_view(), name='lab-test-category-detail'),

    # Lab Test Parameter URLs
    path('lab-test-parameters/', TestParameterCreateView.as_view(), name='lab-test-parameter-list-create'),
    path('lab-test-parameters/<int:parameter_id>/', TestParameterCreateView.as_view(), name='lab-test-parameter-detail'),

    # Lab Reference Range URLs
    path('lab-reference-ranges/', ReferenceRangeCreateView.as_view(), name='lab-reference-range-list-create'),
    path('lab-reference-ranges/<int:range_id>/', ReferenceRangeCreateView.as_view(), name='lab-reference-range-detail'),

    # Lab Test Data & Billing URLs
    path('lab-test-data/', LabDepartmentSerializerView.as_view(), name='lab-test-data-list'),
    path('lab-billing/', Lab_Items.as_view(), name='lab-billing'),

    # ============================================================================
    # LAB TEST ORDER URLs (External Lab Management)
    # ============================================================================
    # Lightweight Lab Tests List (for order creation)
    path('lab-tests/', LabTestListView.as_view(), name='lab-tests-simple'),

    # List and Create
    path('lab-test-orders/', LabTestOrderView.as_view(), name='lab-test-order-list-create'),

    # Detail, Update, Delete
    path('lab-test-orders/<int:order_id>/', LabTestOrderView.as_view(), name='lab-test-order-detail'),

    # Payment Transaction
    path('lab-test-orders/<int:order_id>/payment/', LabPaymentView.as_view(), name='lab-test-order-payment'),

    # PDF Result Upload
    path('lab-test-orders/<int:order_id>/upload-result/', LabResultUploadView.as_view(), name='lab-test-order-upload-result'),

    # Patient Lab Results
    path('patients/<int:patient_id>/lab-results/', PatientLabResultsView.as_view(), name='patient-lab-results'),

    # ============================================================================
    # PATIENT MEDICINE RETURN URLs
    # ============================================================================
    path('medicine-returns/', MedicineReturnCreateView.as_view(), name='medicine-return-create'),
    path('medicine-returns/list/', MedicineReturnListView.as_view(), name='medicine-return-list'),
    path('medicine-returns/<int:return_id>/', MedicineReturnDetailView.as_view(), name='medicine-return-detail'),
    path('medicine-returns/report/', MedicineReturnReportView.as_view(), name='medicine-return-report'),

    # ============================================================================
    # STOCK ALLOCATION & TRANSFER URLs
    # ============================================================================
    path('stock-allocate/', StockAllocationView.as_view(), name='stock-allocate'),
    path('stock-transfers/', StockTransferCreateView.as_view(), name='stock-transfer-create'),
    path('stock-transfers/list/', StockTransferListView.as_view(), name='stock-transfer-list'),
    path('stock-allocation-status/', StockAllocationStatusView.as_view(), name='stock-allocation-status'),

    # ============================================================================
    # AUDIT LOG URLs
    # ============================================================================
    path('stock-audit-log/', MedicationStockAuditLogView.as_view(), name='stock-audit-log'),

    # ============================================================================
    # INVENTORY REPORTS & ANALYTICS URLs
    # ============================================================================
    path('reports/inventory-valuation/', InventoryValuationReportView.as_view(), name='inventory-valuation-report'),
    path('reports/fast-moving/', FastMovingMedicationsReportView.as_view(), name='fast-moving-report'),
    path('reports/slow-moving/', SlowMovingMedicationsReportView.as_view(), name='slow-moving-report'),
    path('reports/stock-aging/', StockAgingReportView.as_view(), name='stock-aging-report'),
    path('reports/expiry-alerts/', ExpiryAlertReportView.as_view(), name='expiry-alert-report'),
    path('reports/expiry-date-filter/', MedicationExpiryDateFilterView.as_view(), name='expiry-date-filter'),
    path('reports/low-stock-alerts/', LowStockAlertReportView.as_view(), name='low-stock-alert-report'),
]