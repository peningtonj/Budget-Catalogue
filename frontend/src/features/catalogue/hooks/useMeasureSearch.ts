import { useQuery } from '@tanstack/react-query'

import { searchMeasures } from '../../../lib/api/measures'
import type { MeasureSearchFilters } from '../types'


export function useMeasureSearch(filters: MeasureSearchFilters) {
  return useQuery({
    queryKey: ['measure-search', filters],
    queryFn: () => searchMeasures(filters),
  })
}
