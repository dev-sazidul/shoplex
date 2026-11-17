import { CustomerOrderDetail } from "@shoplex/ui/CustomerCart";
export const metadata = { title: "Order details | SHOPLEX", robots: { index: false, follow: false } };
type PageProps = { params: Promise<{ orderId: string }> };
export default async function OrderPage({ params }: PageProps) { const { orderId } = await params; return <CustomerOrderDetail orderId={orderId} />; }
