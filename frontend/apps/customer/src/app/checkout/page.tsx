import { CustomerCart } from "@shoplex/ui/CustomerCart";
export const metadata = { title: "Checkout | SHOPLEX", robots: { index: false, follow: false } };
export default function CheckoutPage() { return <CustomerCart checkout />; }
