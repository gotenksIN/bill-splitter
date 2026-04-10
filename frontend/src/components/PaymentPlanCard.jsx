import React from "react";
import { formatCurrency } from "../utils/currency";

const PaymentPlanCard = ({ plan }) => {
  const totalToPay = plan.payments.reduce((sum, p) => sum + p.amount, 0);

  return (
    <div className="border-2 border-gray-300 dark:border-gray-700 p-6">
      <div className="mb-4">
        {/* <div className="text-xs text-gray-700 dark:text-gray-400 mb-1 font-mono tracking-wider">OWES</div>*/}
        <h3 className="text-lg font-normal text-gray-900 dark:text-gray-100">{plan.name}</h3>
        <p className="text-sm text-gray-900 dark:text-gray-100 font-mono mt-1">owes {formatCurrency(totalToPay)}</p>
      </div>

      <div className="space-y-2">
        {plan.payments.map((payment, pIndex) => (
          <div
            key={payment.to}
            className="flex items-center justify-between py-2 border-t-2 border-gray-300 dark:border-gray-700"
          >
            <span className="text-gray-800 dark:text-gray-200">→ {payment.to}</span>
            <span className="text-gray-900 dark:text-gray-100 font-mono">{formatCurrency(payment.amount)}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PaymentPlanCard;
