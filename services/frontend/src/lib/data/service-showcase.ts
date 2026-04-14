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

export const demoServiceCategories: ServiceCategoryItem[] = [
  {
    id: 1,
    name: 'Motor',
    description: 'Servicios preventivos y correctivos para rendimiento y lubricación.',
    icon: '🧰',
    order: 1,
    services_count: 3,
    workshops_count: 2,
  },
  {
    id: 2,
    name: 'Diagnóstico',
    description: 'Scanner, pruebas inteligentes y confirmación técnica.',
    icon: '🧠',
    order: 2,
    services_count: 2,
    workshops_count: 1,
  },
  {
    id: 3,
    name: 'Frenos',
    description: 'Seguridad, revisión preventiva y reparación rápida.',
    icon: '🛑',
    order: 3,
    services_count: 2,
    workshops_count: 1,
  },
  {
    id: 4,
    name: 'Aire Acondicionado',
    description: 'Carga, mantenimiento y limpieza del circuito.',
    icon: '❄️',
    order: 4,
    services_count: 1,
    workshops_count: 1,
  },
];

export const demoServiceListings: ServiceListing[] = [
  {
    id: 901,
    serviceSlug: 'cambio-aceite-premium',
    serviceName: 'Cambio de aceite premium + checklist',
    category: 'Motor',
    serviceType: 'maintenance',
    workshopId: 101,
    workshopSlug: 'torque-lab-surco',
    workshopName: 'Torque Lab Surco',
    workshopHeadline: 'Mantenimiento programado con trazabilidad y ERP.',
    district: 'Surco',
    province: 'Lima',
    department: 'Lima',
    priceMin: 170,
    priceMax: 260,
    durationMin: 55,
    verified: true,
    specialized: true,
    erpIntegrated: true,
    certified: true,
    totalJobs: 164,
    avgRating: 4.9,
    successRate: 97.4,
    repeatFailureRate: 1.9,
    yearsExperience: 12,
    serviceLevel: 'ADVANCED',
    commerceLevel: 'SELLER',
    vehicleExpertise: ['Toyota Corolla', 'Toyota Hilux', 'Multimarca'],
    trustNotes: ['Checklist digital', 'Historial por placa', 'Garantía documentada'],
  },
  {
    id: 902,
    serviceSlug: 'mantenimiento-ac-eco',
    serviceName: 'Mantenimiento A/C con sanitización',
    category: 'Aire Acondicionado',
    serviceType: 'maintenance',
    workshopId: 101,
    workshopSlug: 'torque-lab-surco',
    workshopName: 'Torque Lab Surco',
    workshopHeadline: 'Mantenimiento programado con trazabilidad y ERP.',
    district: 'Surco',
    province: 'Lima',
    department: 'Lima',
    priceMin: 150,
    priceMax: 240,
    durationMin: 70,
    verified: true,
    specialized: false,
    erpIntegrated: true,
    certified: true,
    totalJobs: 92,
    avgRating: 4.8,
    successRate: 95.2,
    repeatFailureRate: 2.8,
    yearsExperience: 12,
    serviceLevel: 'ADVANCED',
    commerceLevel: 'SELLER',
    vehicleExpertise: ['Toyota Corolla', 'Hyundai Tucson', 'Kia Sportage'],
    trustNotes: ['Prueba térmica', 'Filtro revisado', 'Fotografía antes/después'],
  },
  {
    id: 903,
    serviceSlug: 'scanner-avanzado',
    serviceName: 'Scanner avanzado y diagnóstico guiado',
    category: 'Diagnóstico',
    serviceType: 'diagnostic',
    workshopId: 102,
    workshopSlug: 'electrodrive-miraflores',
    workshopName: 'ElectroDrive Miraflores',
    workshopHeadline: 'Especialistas en electrónica, módulos y fallas intermitentes.',
    district: 'Miraflores',
    province: 'Lima',
    department: 'Lima',
    priceMin: 110,
    priceMax: 180,
    durationMin: 40,
    verified: true,
    specialized: true,
    erpIntegrated: true,
    certified: false,
    totalJobs: 138,
    avgRating: 4.8,
    successRate: 96.1,
    repeatFailureRate: 2.1,
    yearsExperience: 9,
    serviceLevel: 'MANAGED',
    commerceLevel: 'SELLER',
    vehicleExpertise: ['Toyota Yaris', 'Chevrolet Onix', 'Nissan Versa'],
    trustNotes: ['Informe de códigos', 'Prueba de ruta', 'Recomendación priorizada'],
  },
  {
    id: 904,
    serviceSlug: 'alternador-bateria',
    serviceName: 'Revisión de alternador y batería',
    category: 'Electricidad Automotriz',
    serviceType: 'repair',
    workshopId: 102,
    workshopSlug: 'electrodrive-miraflores',
    workshopName: 'ElectroDrive Miraflores',
    workshopHeadline: 'Especialistas en electrónica, módulos y fallas intermitentes.',
    district: 'Miraflores',
    province: 'Lima',
    department: 'Lima',
    priceMin: 190,
    priceMax: 340,
    durationMin: 80,
    verified: true,
    specialized: true,
    erpIntegrated: true,
    certified: false,
    totalJobs: 101,
    avgRating: 4.7,
    successRate: 94.6,
    repeatFailureRate: 3.4,
    yearsExperience: 9,
    serviceLevel: 'MANAGED',
    commerceLevel: 'SELLER',
    vehicleExpertise: ['Nissan Frontier', 'Toyota Hilux', 'Multimarca'],
    trustNotes: ['Carga y fuga', 'Prueba de arranque', 'Piezas compatibles'],
  },
  {
    id: 905,
    serviceSlug: 'revision-frenos-360',
    serviceName: 'Revisión de frenos 360°',
    category: 'Frenos',
    serviceType: 'repair',
    workshopId: 103,
    workshopSlug: 'brakepoint-surquillo',
    workshopName: 'BrakePoint Surquillo',
    workshopHeadline: 'Centro especializado en frenos, suspensión y seguridad vial.',
    district: 'Surquillo',
    province: 'Lima',
    department: 'Lima',
    priceMin: 140,
    priceMax: 210,
    durationMin: 65,
    verified: true,
    specialized: true,
    erpIntegrated: false,
    certified: true,
    totalJobs: 187,
    avgRating: 4.9,
    successRate: 98.1,
    repeatFailureRate: 1.3,
    yearsExperience: 15,
    serviceLevel: 'ADVANCED',
    commerceLevel: 'SELLER',
    vehicleExpertise: ['Toyota Corolla', 'Kia Rio', 'Chevrolet Aveo'],
    trustNotes: ['Banco de pruebas', 'Control de torque', 'Prioridad seguridad'],
  },
  {
    id: 906,
    serviceSlug: 'cambio-pastillas-express',
    serviceName: 'Cambio de pastillas express',
    category: 'Frenos',
    serviceType: 'repair',
    workshopId: 103,
    workshopSlug: 'brakepoint-surquillo',
    workshopName: 'BrakePoint Surquillo',
    workshopHeadline: 'Centro especializado en frenos, suspensión y seguridad vial.',
    district: 'Surquillo',
    province: 'Lima',
    department: 'Lima',
    priceMin: 180,
    priceMax: 320,
    durationMin: 75,
    verified: true,
    specialized: true,
    erpIntegrated: false,
    certified: true,
    totalJobs: 144,
    avgRating: 4.9,
    successRate: 97.2,
    repeatFailureRate: 1.7,
    yearsExperience: 15,
    serviceLevel: 'ADVANCED',
    commerceLevel: 'SELLER',
    vehicleExpertise: ['Toyota Yaris', 'Hyundai Accent', 'Kia Cerato'],
    trustNotes: ['Prueba de frenado', 'Revisión de discos', 'Entrega rápida'],
  },
];

export function getServiceListingsOrDemo(listings?: ServiceListing[] | null): ServiceListing[] {
  return listings && listings.length > 0 ? listings : demoServiceListings;
}

export function getServiceCategoriesOrDemo(categories?: ServiceCategoryItem[] | null): ServiceCategoryItem[] {
  return categories && categories.length > 0 ? categories : demoServiceCategories;
}

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
  let score = 0;

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
