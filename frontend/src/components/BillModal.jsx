import React, { useState, useEffect } from "react";
import { X, Upload, Plus } from "lucide-react";
import ItemForm from "./ItemForm";
import { uploadReceipt } from "../utils/api";

const BillModal = ({
  show,
  editingBill,
  onClose,
  onSave,
  showToast,
}) => {
  const [paidBy, setPaidBy] = useState("");
  const [taxRate, setTaxRate] = useState("5");
  const [serviceCharge, setServiceCharge] = useState("0");
  const [items, setItems] = useState([{ id: crypto.randomUUID(), name: "", price: 0, quantity: 1, consumed_by: [] }]);
  const [amountPaid, setAmountPaid] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    if (show) {
      if (editingBill) {
        setPaidBy(editingBill.paid_by);
        setTaxRate((editingBill.tax_rate * 100).toString());
        setServiceCharge((editingBill.service_charge * 100).toString());
        setItems(editingBill.items);
        setAmountPaid(editingBill.amount_paid != null ? String(editingBill.amount_paid) : "");
      } else {
        setPaidBy("");
        setTaxRate("5");
        setServiceCharge("0");
        setItems([{ id: crypto.randomUUID(), name: "", price: 0, quantity: 1, consumed_by: [] }]);
        setAmountPaid("");
      }
    }
  }, [show, editingBill]);

  useEffect(() => {
    if (!show || isUploading) return;

    const handlePaste = (e) => {
      const clipboardItems = e.clipboardData?.items;
      if (!clipboardItems) return;

      for (let i = 0; i < clipboardItems.length; i++) {
        if (clipboardItems[i].type.indexOf("image") !== -1) {
          const file = clipboardItems[i].getAsFile();
          if (file) {
            e.preventDefault();
            handleUploadReceipt({ target: { files: [file] } });
            break;
          }
        }
      }
    };

    document.addEventListener("paste", handlePaste);
    return () => document.removeEventListener("paste", handlePaste);
  }, [show, isUploading]);

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
      setAmountPaid(ocrData.amount_paid.toString());

      showToast("Receipt scanned! Please add who consumed each item.", "success");
    } catch (error) {
      console.error("OCR error:", error);
      showToast("Failed to scan receipt. Please try again.");
    } finally {
      setIsUploading(false);
    }
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
    newItems[index] = { ...newItems[index], [field]: value };
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

  const handleSave = () => {
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
      id: editingBill ? editingBill.id : Date.now().toString(),
      paid_by: paidBy.trim(),
      tax_rate: parseFloat(taxRate) / 100,
      service_charge: parseFloat(serviceCharge) / 100,
      items: validItems,
      amount_paid: parseFloat(amountPaid),
    };

    onSave(bill);
  };

  return (
    <div
      className={`${show ? "block" : "hidden"} fixed inset-0 z-50 md:static md:z-auto bg-white dark:bg-stone-900 md:border-2 md:border-gray-900 dark:border-gray-200 h-full overflow-y-auto`}
    >
      <div className="border-b-2 border-gray-900 dark:border-gray-200 p-6 flex justify-between items-center">
        <h2 className="text-lg font-mono text-gray-900 dark:text-gray-100">
          {editingBill ? "edit bill" : "new bill"}
        </h2>
        <button
          onClick={onClose}
          className="text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
        >
          <X size={20} strokeWidth={2} />
        </button>
      </div>

      <div className="p-6 space-y-6">
        {/* OCR Upload */}
        <div className="border-2 border-dashed border-gray-400 dark:border-gray-600 p-4 hover:border-gray-900 dark:hover:border-gray-300 transition-colors">
          <label className="flex items-center gap-3 cursor-pointer">
            <Upload size={18} className="text-gray-700 dark:text-gray-300" strokeWidth={2} />
            <div className="flex-1">
              <p className="text-sm text-gray-900 dark:text-gray-100">
                {isUploading ? "scanning receipt..." : "upload or paste receipt"}
              </p>
              <p className="text-xs text-gray-700 dark:text-gray-400 mt-0.5">auto-fill using OCR (ctrl+v)</p>
            </div>
            <input
              type="file"
              accept="image/jpeg,image/png"
              onChange={handleUploadReceipt}
              className="hidden"
              disabled={isUploading}
            />
          </label>
        </div>

        {/* Paid By */}
        <div>
          <label className="block text-xs text-gray-700 dark:text-gray-400 mb-2 font-mono tracking-wider">
            PAID BY
          </label>
          <input
            type="text"
            value={paidBy}
            onChange={(e) => setPaidBy(e.target.value)}
            placeholder="enter name"
            className="w-full px-0 py-2 bg-transparent border-b-2 border-gray-400 dark:border-gray-600 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-500 focus:outline-none focus:border-gray-900 dark:focus:border-gray-300 transition-colors"
          />
        </div>

        {/* Amount Paid */}
        <div>
          <label className="block text-xs text-gray-700 dark:text-gray-400 mb-2 font-mono tracking-wider">
            AMOUNT PAID
          </label>
          <input
            type="number"
            value={amountPaid}
            onChange={(e) => setAmountPaid(e.target.value)}
            placeholder="0.00"
            className="w-full px-0 py-2 bg-transparent border-b-2 border-gray-400 dark:border-gray-600 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-500 focus:outline-none focus:border-gray-900 dark:focus:border-gray-300 transition-colors font-mono"
            min="0"
            step="0.01"
          />
        </div>

        {/* Tax & Service */}
        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-xs text-gray-700 dark:text-gray-400 mb-2 font-mono tracking-wider">
              TAX (%)
            </label>
            <input
              type="number"
              value={taxRate}
              onChange={(e) => setTaxRate(e.target.value)}
              placeholder="5.0"
              className="w-full px-0 py-2 bg-transparent border-b-2 border-gray-400 dark:border-gray-600 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-500 focus:outline-none focus:border-gray-900 dark:focus:border-gray-300 transition-colors font-mono"
              min="0"
              max="100"
              step="0.1"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-700 dark:text-gray-400 mb-2 font-mono tracking-wider">
              SERVICE (%)
            </label>
            <input
              type="number"
              value={serviceCharge}
              onChange={(e) => setServiceCharge(e.target.value)}
              placeholder="10.0"
              className="w-full px-0 py-2 bg-transparent border-b-2 border-gray-400 dark:border-gray-600 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-500 focus:outline-none focus:border-gray-900 dark:focus:border-gray-300 transition-colors font-mono"
              min="0"
              max="100"
              step="0.1"
            />
          </div>
        </div>

        {/* Items Section */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs text-gray-700 dark:text-gray-400 font-mono tracking-wider">ITEMS</h3>
          </div>

          <div className="space-y-4">
            {items.map((item, index) => (
              <ItemForm
                key={item.id || index}
                item={item}
                index={index}
                onItemChange={handleItemChange}
                onDelete={handleDeleteItem}
                canDelete={items.length > 1}
                onConsumerKeyDown={handleConsumerKeyDown}
                onRemoveConsumer={removeConsumer}
              />
            ))}
          </div>

          <button
            onClick={handleAddItem}
            className="w-full mt-4 py-3 border-2 border-dashed border-gray-400 dark:border-gray-600 text-gray-800 dark:text-gray-300 hover:border-gray-900 dark:hover:border-gray-300 hover:text-gray-900 dark:hover:text-gray-100 transition-colors flex items-center justify-center gap-2 text-sm"
          >
            <Plus size={16} strokeWidth={2} />
            add item
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4 pt-4">
          <button
            onClick={handleSave}
            className="flex-1 py-3 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors"
          >
            save bill
          </button>
          <button
            onClick={onClose}
            className="px-6 py-3 border-2 border-gray-400 dark:border-gray-600 text-gray-800 dark:text-gray-300 hover:border-gray-900 dark:hover:border-gray-300 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
            aria-label="Cancel"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default BillModal;
