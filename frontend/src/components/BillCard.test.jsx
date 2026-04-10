import { render, screen } from "@testing-library/react";
import React from "react";
import BillCard from "./BillCard";

describe("BillCard", () => {
  it("renders the correct paid amount and name", () => {
    const mockBill = {
      id: "1",
      paid_by: "John",
      amount_paid: 150.5,
      tax_rate: 0.1,
      service_charge: 0.05,
      items: [
        { name: "Burger", price: 10, quantity: 2 },
        { name: "Fries", price: 5, quantity: 1 }
      ]
    };

    render(<BillCard bill={mockBill} onEdit={() => {}} onDelete={() => {}} />);
    
    expect(screen.getByText("John")).toBeDefined();
    
    // Check for correct numbers without binding to a specific currency symbol
    // since the formatting changes dynamically based on test environment locale
    expect(screen.getByText(/150\.50/)).toBeDefined();
    expect(screen.getByText("2 × Burger")).toBeDefined();
    expect(screen.getByText(/20\.00/)).toBeDefined(); // 10 * 2
  });
});