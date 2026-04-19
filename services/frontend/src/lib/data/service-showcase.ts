import type {
  CommerceLevel,
  ServiceCategoryItem,
  ServiceLevel,
  ServiceListing,
  ServiceType,
} from '$lib/api/types';

export type ProblemKey =
  | 'brakes'
  | 'maintenance'
  | 'diagnostic'
  | 'electrical'
  | 'ac'
  | 'transmission'
  | 'engine';

export type ProblemOption = {
  key: ProblemKey;
  label: string;
  description: string;
  icon: string;
  category: string;
  serviceType: ServiceType;
  symptoms: string[];
  relatedServices: string[];
};

export type TemplateCard = {
  title: string;
  description: string;
  file: string;
  href: string;
  cta: string;
};

export type ScoredListing = ServiceListing & { score: number };

export type WorkshopAggregate = {
  workshopId: number;
  workshopSlug: string;
  workshopName: string;
  workshopHeadline: string;
  district: string;
  verified: boolean;
  erpIntegrated: boolean;
  certified: boolean;
  yearsExperience: number;
  serviceLevel: ServiceLevel;
  commerceLevel: CommerceLevel;
  services: ServiceListing[];
  featuredServices: string[];
  lowestPrice: number | null;
  highestPrice: number | null;
  highestSuccessRate: number;
  averageRepeatFailureRate: number;
  totalJobs: number;
  vehicleExpertise: string[];
  trustNotes: string[];
  topScore: number | null;
};

export type ServiceAggregate = {
  serviceSlug: string;
  serviceName: string;
  category: string;
  serviceType: ServiceType;
  workshops: ServiceListing[];
  minPrice: number | null;
  maxPrice: number | null;
  minDuration: number;
  highestSuccessRate: number;
  averageRepeatFailureRate: number;
  totalJobs: number;
  districts: string[];
  vehicleExpertise: string[];
  trustNotes: string[];
};

export const demoWorkshopSlug = 'torque-lab-surco';
export const demoServiceSlug = 'cambio-aceite-premium';

export const problemOptions: ProblemOption[] = [
  {
    key: 'brakes',
    label: 'Frenos y seguridad',
    description: 'Pedal esponjoso, chirridos o frenado irregular.',
    icon: '🛑',
    category: 'Frenos',
    serviceType: 'repair',
    symptoms: ['Ruido al frenar', 'Vibración', 'Pedal largo'],
    relatedServices: ['cambio-pastillas-express', 'revision-frenos-360', 'cambio-discos-pro'],
  },
  {
    key: 'maintenance',
    label: 'Mantenimiento preventivo',
    description: 'Cambio de aceite, filtros y revisión general.',
    icon: '🧰',
    category: 'Motor',
    serviceType: 'maintenance',
    symptoms: ['Cambio periódico', 'Checklist', 'Afinamiento'],
    relatedServices: ['cambio-aceite-premium', 'afinamiento-multimarca'],
  },
  {
    key: 'diagnostic',
    label: 'Diagnóstico inteligente',
    description: 'Testigo encendido o falla sin causa clara.',
    icon: '🧠',
    category: 'Diagnóstico',
    serviceType: 'diagnostic',
    symptoms: ['Check engine', 'Consumo alto', 'Falla intermitente'],
    relatedServices: ['scanner-avanzado', 'diagnostico-electrico-pro'],
  },
  {
    key: 'electrical',
    label: 'Electricidad automotriz',
    description: 'Problemas de batería, alternador o sensores.',
    icon: '⚡',
    category: 'Electricidad Automotriz',
    serviceType: 'repair',
    symptoms: ['No enciende', 'Luces inestables', 'Falla eléctrica'],
    relatedServices: ['alternador-bateria', 'diagnostico-electrico-pro'],
  },
  {
    key: 'ac',
    label: 'Aire acondicionado',
    description: 'Baja refrigeración o mantenimiento del sistema A/C.',
    icon: '❄️',
    category: 'Aire Acondicionado',
    serviceType: 'maintenance',
    symptoms: ['No enfría', 'Mal olor', 'Carga de gas'],
    relatedServices: ['mantenimiento-ac-eco'],
  },
  {
    key: 'transmission',
    label: 'Transmisión',
    description: 'Golpes, patinamiento o mantenimiento de caja.',
    icon: '⚙️',
    category: 'Transmisión',
    serviceType: 'repair',
    symptoms: ['Golpe al cambiar', 'Patina', 'Mantenimiento de caja'],
    relatedServices: ['reparacion-transmision-direct'],
  },
  {
    key: 'engine',
    label: 'Motor y rendimiento',
    description: 'Pérdida de potencia, humo o reparación mayor.',
    icon: '🔧',
    category: 'Motor',
    serviceType: 'repair',
    symptoms: ['Baja potencia', 'Humo', 'Consumo irregular'],
    relatedServices: ['overhaul-ligero', 'afinamiento-multimarca'],
  },
];

export const vehicleCatalog: Record<string, Array<{ value: string; label: string }>> = {
  Toyota: [
    { value: 'Corolla', label: 'Corolla' },
    { value: 'Yaris', label: 'Yaris' },
    { value: 'Hilux', label: 'Hilux' },
    { value: 'RAV4', label: 'RAV4' },
  ],
  Hyundai: [
    { value: 'Accent', label: 'Accent' },
    { value: 'Elantra', label: 'Elantra' },
    { value: 'Tucson', label: 'Tucson' },
  ],
  Kia: [
    { value: 'Rio', label: 'Rio' },
    { value: 'Cerato', label: 'Cerato' },
    { value: 'Sportage', label: 'Sportage' },
  ],
  Chevrolet: [
    { value: 'Aveo', label: 'Aveo' },
    { value: 'Onix', label: 'Onix' },
    { value: 'Captiva', label: 'Captiva' },
  ],
  Nissan: [
    { value: 'Versa', label: 'Versa' },
    { value: 'Sentra', label: 'Sentra' },
    { value: 'Frontier', label: 'Frontier' },
  ],
};

export const budgetOptions = [
  { value: 'all', label: 'Cualquier presupuesto' },
  { value: 'economy', label: 'Hasta S/ 150' },
  { value: 'balanced', label: 'Hasta S/ 300' },
  { value: 'premium', label: 'Servicios premium' },
] as const;

export const serviceTypeLabels: Record<ServiceType, string> = {
  maintenance: 'Mantenimiento',
  repair: 'Reparación',
  diagnostic: 'Diagnóstico',
};

export const serviceLevelLabels: Record<ServiceLevel, string> = {
  BASIC: 'Basic',
  MANAGED: 'Managed',
  ADVANCED: 'Advanced',
};

export const commerceLevelLabels: Record<CommerceLevel, string> = {
  NONE: 'Sin comercio',
  BUYER: 'Comprador',
  B2B_BUYER: 'Comprador B2B',
  SELLER: 'Vendedor',
};

export const templateCards: TemplateCard[] = [
  {
    title: '1. Entrada guiada',
    description: 'Wizard corto orientado a problema + vehículo para reducir fricción desde la home de servicios.',
    file: 'services_entry',
    href: '/servicios/entrada-guiada',
    cta: 'Abrir wizard',
  },
  {
    title: '2. Resultados filtrables',
    description: 'Listado con toggle por servicio o por taller, badges de confianza y filtros profesionales.',
    file: 'services_results',
    href: '/servicios/resultados',
    cta: 'Explorar resultados',
  },
  {
    title: '3. Perfil del taller',
    description: 'Detalle de taller con expertise vehicular, horarios, historial agregado y catálogo publicado.',
    file: 'workshop_detail',
    href: `/servicios/taller/${demoWorkshopSlug}`,
    cta: 'Ver perfil',
  },
  {
    title: '4. Detalle del servicio',
    description: 'Página pro para explicar el servicio y mostrar talleres que lo ofrecen con confianza real.',
    file: 'service_detail',
    href: `/servicios/servicio/${demoServiceSlug}`,
    cta: 'Ver servicio',
  },
];

export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return 'Consultar';
  return `S/ ${value.toLocaleString('es-PE')}`;
}

export function formatPriceRange(min: number | null | undefined, max: number | null | undefined): string {
  if (min == null && max == null) return 'Precio a consultar';
  if (min == null) return `Hasta ${formatCurrency(max)}`;
  if (max == null) return `Desde ${formatCurrency(min)}`;
  return `${formatCurrency(min)} – ${formatCurrency(max)}`;
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  return remaining ? `${hours}h ${remaining}min` : `${hours}h`;
}

export function confidenceLabel(score: number): string {
  if (score >= 120) return 'Recomendación alta';
  if (score >= 95) return 'Muy buen match';
  if (score >= 75) return 'Buen match';
  return 'Explorable';
}

export function budgetMatches(listing: ServiceListing, selectedBudget: string): boolean {
  const basePrice = listing.priceMin ?? Number.POSITIVE_INFINITY;
  if (selectedBudget === 'all') return true;
  if (selectedBudget === 'economy') return basePrice <= 150;
  if (selectedBudget === 'balanced') return basePrice <= 300;
  return basePrice > 300;
}

export function vehicleMatches(listing: ServiceListing, selectedBrand: string, selectedModel: string): boolean {
  const brand = selectedBrand.toLowerCase();
  const model = selectedModel.toLowerCase();

  return listing.vehicleExpertise.some((entry) => {
    const current = entry.toLowerCase();
    return current.includes(brand) || current.includes(model) || current.includes('multimarca');
  });
}

export function scoreListing(
  listing: ServiceListing,
  options: {
    problemKey?: ProblemKey;
    selectedCategory?: string;
    selectedBrand: string;
    selectedModel: string;
    selectedDistrict?: string;
    selectedProvince?: string;
    selectedDepartment?: string;
    search?: string;
  }
): number {
  // Base: server-side materialized score (0–100) scaled to 0–40 pts
  let score = (listing.workshopScore ?? 0) * 0.4;

  if (options.problemKey) {
    const selectedProblemConfig = problemOptions.find((option) => option.key === options.problemKey) ?? problemOptions[0];
    if (selectedProblemConfig.relatedServices.includes(listing.serviceSlug)) score += 48;
    if (listing.category === selectedProblemConfig.category) score += 22;
    if (listing.serviceType === selectedProblemConfig.serviceType) score += 14;
  } else if (options.selectedCategory && options.selectedCategory !== 'all') {
    if (listing.category === options.selectedCategory) score += 36;
  }

  if (vehicleMatches(listing, options.selectedBrand, options.selectedModel)) score += 24;
  if (listing.specialized) score += 8;
  if (listing.verified) score += 10;
  if (listing.erpIntegrated) score += 6;
  if (listing.certified) score += 6;

  score += Math.min(20, listing.totalJobs / 8);
  score += listing.successRate / 10;
  score -= listing.repeatFailureRate * 3;

  if (options.selectedDistrict && options.selectedDistrict !== 'all' && listing.district === options.selectedDistrict) score += 12;
  else if (options.selectedProvince && options.selectedProvince !== 'all' && listing.province === options.selectedProvince) score += 6;
  else if (options.selectedDepartment && options.selectedDepartment !== 'all' && listing.department === options.selectedDepartment) score += 3;
  if (options.search?.trim()) {
    const haystack = `${listing.serviceName} ${listing.workshopName} ${listing.category} ${listing.workshopHeadline}`.toLowerCase();
    if (haystack.includes(options.search.trim().toLowerCase())) score += 8;
  }

  return Number(score.toFixed(1));
}

export function buildWorkshopAggregate(listings: ServiceListing[]): WorkshopAggregate {
  const [first] = listings;

  return {
    workshopId: first.workshopId,
    workshopSlug: first.workshopSlug,
    workshopName: first.workshopName,
    workshopHeadline: first.workshopHeadline,
    district: first.district,
    verified: listings.some((listing) => listing.verified),
    erpIntegrated: listings.some((listing) => listing.erpIntegrated),
    certified: listings.some((listing) => listing.certified),
    yearsExperience: Math.max(...listings.map((listing) => listing.yearsExperience)),
    serviceLevel: listings.reduce((current, listing) => rankServiceLevel(listing.serviceLevel) > rankServiceLevel(current) ? listing.serviceLevel : current, first.serviceLevel),
    commerceLevel: first.commerceLevel,
    services: [...listings],
    featuredServices: uniqueValues(listings.map((listing) => listing.serviceName), 4),
    lowestPrice: numericMin(listings.map((listing) => listing.priceMin)),
    highestPrice: numericMax(listings.map((listing) => listing.priceMax)),
    highestSuccessRate: Math.max(...listings.map((listing) => listing.successRate)),
    averageRepeatFailureRate: average(listings.map((listing) => listing.repeatFailureRate)),
    totalJobs: listings.reduce((sum, listing) => sum + listing.totalJobs, 0),
    vehicleExpertise: uniqueValues(listings.flatMap((listing) => listing.vehicleExpertise), 8),
    trustNotes: uniqueValues(listings.flatMap((listing) => listing.trustNotes), 8),
    topScore: numericMax(
      listings.map((listing) => ('score' in listing ? (listing as ScoredListing).score : null))
    ),
  };
}

export function groupWorkshopAggregates(listings: ServiceListing[]): WorkshopAggregate[] {
  const grouped = listings.reduce<Record<string, ServiceListing[]>>((acc, listing) => {
    if (!acc[listing.workshopSlug]) acc[listing.workshopSlug] = [];
    acc[listing.workshopSlug].push(listing);
    return acc;
  }, {});

  return Object.values(grouped)
    .map((items) => buildWorkshopAggregate(items))
    .sort((a, b) => {
      if (a.topScore != null || b.topScore != null) {
        return (b.topScore ?? 0) - (a.topScore ?? 0);
      }
      return b.highestSuccessRate - a.highestSuccessRate;
    });
}

export function buildServiceAggregate(listings: ServiceListing[]): ServiceAggregate {
  const [first] = listings;

  return {
    serviceSlug: first.serviceSlug,
    serviceName: first.serviceName,
    category: first.category,
    serviceType: first.serviceType,
    workshops: [...listings],
    minPrice: numericMin(listings.map((listing) => listing.priceMin)),
    maxPrice: numericMax(listings.map((listing) => listing.priceMax)),
    minDuration: Math.min(...listings.map((listing) => listing.durationMin)),
    highestSuccessRate: Math.max(...listings.map((listing) => listing.successRate)),
    averageRepeatFailureRate: average(listings.map((listing) => listing.repeatFailureRate)),
    totalJobs: listings.reduce((sum, listing) => sum + listing.totalJobs, 0),
    districts: uniqueValues(listings.map((listing) => listing.district), 6),
    vehicleExpertise: uniqueValues(listings.flatMap((listing) => listing.vehicleExpertise), 8),
    trustNotes: uniqueValues(listings.flatMap((listing) => listing.trustNotes), 8),
  };
}

function average(values: number[]): number {
  if (!values.length) return 0;
  return Number((values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(1));
}

function numericMin(values: Array<number | null | undefined>): number | null {
  const filtered = values.filter((value): value is number => value !== null && value !== undefined);
  return filtered.length ? Math.min(...filtered) : null;
}

function numericMax(values: Array<number | null | undefined>): number | null {
  const filtered = values.filter((value): value is number => value !== null && value !== undefined);
  return filtered.length ? Math.max(...filtered) : null;
}

function uniqueValues(values: string[], limit?: number): string[] {
  const unique = Array.from(new Set(values.filter(Boolean)));
  return limit ? unique.slice(0, limit) : unique;
}

function rankServiceLevel(level: ServiceLevel): number {
  if (level === 'ADVANCED') return 3;
  if (level === 'MANAGED') return 2;
  return 1;
}
