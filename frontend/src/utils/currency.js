export const formatCurrency = (amount) => {
  let locale = "en-IN";
  if (typeof navigator !== "undefined" && navigator.language) {
    locale = navigator.language;
  }

  let currency = "INR"; // Default to Rupee
  const countryMatches = locale.match(/-([A-Z]{2})/i);
  if (countryMatches) {
    const country = countryMatches[1].toUpperCase();
    const currencyMap = {
      US: "USD",
      GB: "GBP",
      AU: "AUD",
      CA: "CAD",
      SG: "SGD",
      NZ: "NZD",
      EU: "EUR",
      DE: "EUR",
      FR: "EUR",
      IT: "EUR",
      ES: "EUR",
      NL: "EUR",
      JP: "JPY",
      CN: "CNY",
      IN: "INR",
    };
    if (currencyMap[country]) {
      currency = currencyMap[country];
    }
  }

  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: currency,
  }).format(amount);
};
