import { CustomerAccount } from "@shoplex/ui/CustomerAccount";
export const metadata = { title: "Payment history | SHOPLEX", robots: { index: false, follow: false } };
export default function PaymentsPage() { return <CustomerAccount section="/account/payments" />; }
