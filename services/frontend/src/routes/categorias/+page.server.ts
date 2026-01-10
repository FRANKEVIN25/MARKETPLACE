import type { PageServerLoad } from './$types';

interface Product {
  id: number;
  nombre?: string;
  name?: string;
  proveedor?: string;
  supplier?: string;
  categoria?: string;
  category?: string;
  precio?: number;
  price?: number;
}

interface ParentData {
  products?: Product[];
  totalCount?: number;
  error?: string | null;
}

export const load: PageServerLoad = async ({ parent }) => {
  const parentData = (await parent()) as ParentData;
  
  return {
    products: parentData?.products || [],
    totalCount: parentData?.totalCount || 0,
    error: parentData?.error || null
  };
};