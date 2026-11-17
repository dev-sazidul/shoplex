import { CustomerAccount } from "@shoplex/ui/CustomerAccount";
export const metadata = { title: "Wishlist | SHOPLEX", robots: { index: false, follow: false } };
export default function WishlistPage() { return <CustomerAccount section="/account/wishlist" />; }
