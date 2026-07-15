import { useQuery } from '@tanstack/react-query'

import { getMeasureDetail } from '../../../lib/api/measures'


export function useMeasureDetail(measureId: number) {
  return useQuery({
    queryKey: ['measure-detail', measureId],
    queryFn: () => getMeasureDetail(measureId),
    enabled: Number.isFinite(measureId),
  })
}
