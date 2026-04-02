export type BusinessActivity =
  | 'workshop'
  | 'parts_supplier'
  | 'retail_store'
  | 'distributor'
  | 'fleet'
  | 'dealer'
  | 'manufacturer'
  | 'insurance'
  | 'other';

export const BUSINESS_ACTIVITY_OPTIONS: Array<{ value: BusinessActivity; label: string }> = [
  { value: 'workshop', label: 'Taller mecánico' },
  { value: 'parts_supplier', label: 'Proveedor de autopartes' },
  { value: 'retail_store', label: 'Tienda de repuestos' },
  { value: 'distributor', label: 'Distribuidor mayorista' },
  { value: 'fleet', label: 'Flota o transporte' },
  { value: 'dealer', label: 'Concesionario' },
  { value: 'manufacturer', label: 'Fabricación o rectificación' },
  { value: 'insurance', label: 'Aseguradora o peritaje' },
  { value: 'other', label: 'Otro rubro automotriz' },
];

export function isBusinessActivity(value: string | null | undefined): value is BusinessActivity {
  return BUSINESS_ACTIVITY_OPTIONS.some((option) => option.value === value);
}

export function normalizeBusinessActivity(value: string | null | undefined): BusinessActivity | '' {
  return isBusinessActivity(value) ? value : '';
}

export function isWorkshopBusinessActivity(value: string | null | undefined): boolean {
  return normalizeBusinessActivity(value) === 'workshop';
}

export function getBusinessActivityLabel(value: string | null | undefined): string {
  const option = BUSINESS_ACTIVITY_OPTIONS.find((item) => item.value === value);
  return option?.label || 'Sin definir';
}