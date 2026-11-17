import { CustomerAccount } from "@shoplex/ui/CustomerAccount";
export const metadata = { title: "My reviews | SHOPLEX", robots: { index: false, follow: false } };
export default function MyReviewsPage() { return <CustomerAccount section="/account/reviews" />; }
