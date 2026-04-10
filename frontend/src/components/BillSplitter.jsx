import React, { useState, useEffect } from "react";
import { Receipt, Plus, ArrowLeft } from "lucide-react";
import BillCard from "./BillCard";
import BillModal from "./BillModal";
import PaymentPlansView from "./PaymentPlansView";
import EmptyState from "./EmptyState";
import { uploadReceipt, calculateSplit } from "../utils/api";

const BillSplitter = () => {
  const [bills, setBills] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editingBillId, setEditingBillId] = useState(null);
  const [paymentPlans, setPaymentPlans] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [paidBy, setPaidBy] = useState("");
  const [taxRate, setTaxRate] = useState("5");
  const [serviceCharge, setServiceCharge] = useState("0");
  const [items, setItems] = useState([{ id: crypto.randomUUID(), name: "", price: 0, quantity: 1, consumed_by: [] }]);
  const [amountPaid, setAmountPaid] = useState("");
  const [toast, setToast] = useState(null);

  const showToast = (message, type = "error") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const resetForm = () => {
    setPaidBy("");
    setTaxRate("5");
    setServiceCharge("0");
    setItems([{ id: crypto.randomUUID(), name: "", price: 0, quantity: 1, consumed_by: [] }]);
    setAmountPaid("");
    setEditingBillId(null);
  };

  const handleAddBill = () => {
    setShowModal(true);
    setShowResults(false);
    setPaymentPlans([]);
    resetForm();
  };

  const handleEditBill = (bill) => {
    setEditingBillId(bill.id);
    setPaidBy(bill.paid_by);
    setTaxRate((bill.tax_rate * 100).toString());
    setServiceCharge((bill.service_charge * 100).toString());
    setItems(bill.items);
    setAmountPaid(bill.amount_paid != null ? String(bill.amount_paid) : "");
    setShowModal(true);
    setShowResults(false);
    setPaymentPlans([]);
  };

  const handleDeleteBill = (id) => {
    setBills(bills.filter((b) => b.id !== id));
  };

  const handleSaveBill = () => {
    if (!paidBy.trim()) {
      showToast("Please enter who paid the bill");
      return;
    }

    if (!amountPaid || parseFloat(amountPaid) <= 0) {
      showToast("Please enter a valid amount paid");
      return;
    }

    const validItems = items.filter(
      (item) => item.name.trim() && item.price > 0 && item.quantity > 0 && item.consumed_by.length > 0,
    );

    if (validItems.length === 0) {
      showToast("Please add at least one valid item with consumers");
      return;
    }

    const bill = {
      id: editingBillId || Date.now().toString(),
      paid_by: paidBy.trim(),
      tax_rate: parseFloat(taxRate) / 100,
      service_charge: parseFloat(serviceCharge) / 100,
      items: validItems,
      amount_paid: parseFloat(amountPaid),
    };

    if (editingBillId) {
      setBills(bills.map((b) => (b.id === editingBillId ? bill : b)));
    } else {
      setBills([...bills, bill]);
    }

    setShowModal(false);
    resetForm();
  };

  const handleAddItem = () => {
    setItems([...items, { id: crypto.randomUUID(), name: "", price: 0, quantity: 1, consumed_by: [] }]);
  };

  const handleDeleteItem = (index) => {
    if (items.length > 1) {
      setItems(items.filter((_, i) => i !== index));
    }
  };

  const handleItemChange = (index, field, value) => {
    const newItems = [...items];
    newItems[index][field] = value;
    setItems(newItems);
  };

  const handleConsumerKeyDown = (index, e) => {
    if (e.key === "Enter" && e.target.value.trim()) {
      e.preventDefault();
      const newItems = [...items];
      const currentConsumers = newItems[index].consumed_by || [];
      const newConsumer = e.target.value.trim();

      if (!currentConsumers.includes(newConsumer)) {
        newItems[index].consumed_by = [...currentConsumers, newConsumer];
        setItems(newItems);
      }
      e.target.value = "";
    }
  };

  const removeConsumer = (itemIndex, consumerName) => {
    const newItems = [...items];
    newItems[itemIndex].consumed_by = newItems[itemIndex].consumed_by.filter((c) => c !== consumerName);
    setItems(newItems);
  };

  const handleUploadReceipt = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);

    try {
      const ocrData = await uploadReceipt(file);

      setTaxRate((ocrData.tax_rate * 100).toString());
      setServiceCharge((ocrData.service_charge * 100).toString());
      setItems(
        ocrData.items.map((item) => ({
          ...item,
          id: crypto.randomUUID(),
          consumed_by: [],
        })),
      );
      // populate amount paid from OCR response if available
      setAmountPaid(ocrData.amount_paid.toString());

      showToast("Receipt scanned! Please add who consumed each item.", "success");
    } catch (error) {
      console.error("OCR error:", error);
      showToast("Failed to scan receipt. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleCalculateSplit = async () => {
    if (bills.length === 0) {
      showToast("Please add at least one bill");
      return;
    }

    try {
      const result = await calculateSplit(bills);
      setPaymentPlans(result.payment_plans);
      setShowResults(true);
    } catch (error) {
      console.error("Split calculation error:", error);
      showToast("Failed to calculate split. Please try again.");
    }
  };

  const handleCloseModal = () => {
    setShowModal(false);
    resetForm();
  };

  return (
    <div className="min-h-screen bg-white dark:bg-stone-900 p-6 lg:p-8 transition-colors">
      <div className="max-w-7xl mx-auto mb-12">
        <div className="flex items-center gap-3 mb-2">
          <Receipt size={24} className="text-gray-900 dark:text-gray-100" strokeWidth={2} />
          <h1 className="text-2xl font-mono text-gray-900 dark:text-gray-100">bill splitter</h1>
        </div>
        <p className="text-sm font-mono text-gray-700 dark:text-gray-400">split bills fairly among friends</p>
      </div>

      <div className="max-w-7xl mx-auto">
        <div className="md:grid md:grid-cols-2 md:gap-8 md:h-[calc(100vh-200px)]">
          <div className={`${showModal || showResults ? 'hidden md:block' : 'block'} border-2 border-gray-900 dark:border-gray-200 p-6 h-full overflow-y-auto`}>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-mono text-gray-900 dark:text-gray-100">bills</h2>
              <span className="text-xs text-gray-700 dark:text-gray-400 font-mono">{bills.length}</span>
            </div>

            <button
              onClick={handleAddBill}
              className="w-full py-3 mb-6 border-2 border-dashed border-gray-400 dark:border-gray-600 text-gray-800 dark:text-gray-300 hover:border-gray-900 dark:hover:border-gray-300 hover:text-gray-900 dark:hover:text-gray-100 transition-colors flex items-center justify-center gap-2 text-sm font-mono"
            >
              <Plus size={16} strokeWidth={2} />
              add new bill
            </button>

            {bills.length === 0 ? (
              <EmptyState message="no bills yet" />
            ) : (
              bills.map((bill) => (
                <BillCard key={bill.id} bill={bill} onEdit={handleEditBill} onDelete={handleDeleteBill} />
              ))
            )}

            <button
              onClick={handleCalculateSplit}
              className="w-full mt-6 py-3 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors disabled:opacity-30 disabled:cursor-not-allowed font-mono"
              disabled={bills.length === 0}
            >
              calculate split
            </button>
          </div>

          <div className={`${!showModal && !showResults ? 'hidden md:block' : 'block'} h-full`}>
            {showModal && (
              <BillModal
                show={showModal}
                editingBillId={editingBillId}
                paidBy={paidBy}
                setPaidBy={setPaidBy}
                taxRate={taxRate}
                setTaxRate={setTaxRate}
                serviceCharge={serviceCharge}
                setServiceCharge={setServiceCharge}
                amountPaid={amountPaid}
                setAmountPaid={setAmountPaid}
                items={items}
                isUploading={isUploading}
                onClose={handleCloseModal}
                onSave={handleSaveBill}
                onUploadReceipt={handleUploadReceipt}
                onAddItem={handleAddItem}
                onItemChange={handleItemChange}
                onDeleteItem={handleDeleteItem}
                onConsumerKeyDown={handleConsumerKeyDown}
                onRemoveConsumer={removeConsumer}
              />
            )}
            {showResults && (
              <div className="h-full flex flex-col space-y-6 md:space-y-0">
                <button
                  onClick={() => setShowResults(false)}
                  className="md:hidden w-full py-3 border-2 border-gray-400 dark:border-gray-600 text-gray-800 dark:text-gray-300 hover:border-gray-900 dark:hover:border-gray-300 hover:text-gray-900 dark:hover:text-gray-100 transition-colors flex items-center justify-center gap-2"
                >
                  <ArrowLeft size={16} strokeWidth={2} />
                  back to bills
                </button>
                <div className="flex-1 overflow-y-auto">
                  <PaymentPlansView paymentPlans={paymentPlans} />
                </div>
                <button
                  onClick={handleAddBill}
                  className="md:hidden w-full py-3 border-2 border-dashed border-gray-400 dark:border-gray-600 text-gray-800 dark:text-gray-300 hover:border-gray-900 dark:hover:border-gray-300 hover:text-gray-900 dark:hover:text-gray-100 transition-colors flex items-center justify-center gap-2 text-sm"
                >
                  <Plus size={16} strokeWidth={2} />
                  add new bill
                </button>
              </div>
            )}
            {!showModal && !showResults && (
              <div className="border-2 border-dashed border-gray-400 dark:border-gray-600 h-full flex flex-col items-center justify-center p-12 hidden md:flex">
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-4 border-2 border-gray-300 dark:border-gray-700 flex items-center justify-center">
                    <Receipt size={24} className="text-gray-400 dark:text-gray-600" strokeWidth={2} />
                  </div>
                  <p className="text-gray-600 dark:text-gray-500 text-sm font-mono">add bills or calculate split</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {toast && (
        <div className={`fixed bottom-4 right-4 p-4 text-white font-mono z-[100] shadow-lg ${toast.type === "error" ? "bg-red-600" : "bg-green-600"}`}>
          {toast.message}
        </div>
      )}
    </div>
  );
};
export default BillSplitter;
