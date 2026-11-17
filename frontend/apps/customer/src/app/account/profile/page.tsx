import { CustomerAccount } from "@shoplex/ui/CustomerAccount";
export const metadata = { title: "Profile | SHOPLEX", robots: { index: false, follow: false } };
export default function ProfilePage() { return <CustomerAccount section="/account/profile" />; }
