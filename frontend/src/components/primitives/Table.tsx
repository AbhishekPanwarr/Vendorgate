import React, { useState } from 'react';
import { ChevronUp, ChevronDown, ChevronLeft, ChevronRight, Filter, X } from 'lucide-react';
import { Skeleton } from './Skeleton';
import { Button } from './Button';

export interface TableColumn<T> {
  key: string;
  header: string;
  render: (item: T, index: number) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  numeric?: boolean;
  sortable?: boolean;
  width?: string;
}

export interface TableFilterChip {
  id: string;
  label: string;
  value: string;
}

export interface TableProps<T> {
  columns: TableColumn<T>[];
  data: T[];
  rowKey: (item: T) => string;
  onRowClick?: (item: T) => void;
  loading?: boolean;
  emptyState?: React.ReactNode;
  compact?: boolean;
  filterChips?: TableFilterChip[];
  onRemoveFilter?: (id: string) => void;
  filterActions?: React.ReactNode;
  pageSize?: number;
  className?: string;
  rowHighlight?: (item: T) => string; // additional row classes e.g. left border
}

export function Table<T>({
  columns,
  data,
  rowKey,
  onRowClick,
  loading = false,
  emptyState,
  compact = false,
  filterChips,
  onRemoveFilter,
  filterActions,
  pageSize = 10,
  className = '',
  rowHighlight,
}: TableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortOrder('desc');
    }
  };

  const totalPages = Math.ceil(data.length / pageSize) || 1;
  const startIdx = (currentPage - 1) * pageSize;
  const paginatedData = data.slice(startIdx, startIdx + pageSize);

  const rowHeightClass = compact ? 'h-10' : 'h-[52px]';

  return (
    <div className={`w-full flex flex-col rounded-[8px] border border-border bg-surface overflow-hidden ${className}`}>
      {/* Filter bar */}
      {(filterChips?.length || filterActions) && (
        <div className="flex flex-wrap items-center justify-between gap-2 p-3 px-4 border-b border-border-subtle bg-subtle/20">
          <div className="flex flex-wrap items-center gap-1.5">
            {filterChips?.map(chip => (
              <span
                key={chip.id}
                className="inline-flex items-center gap-1.5 h-6 px-2 rounded-full bg-surface border border-border text-[12px] text-text-primary"
              >
                <span className="text-text-secondary">{chip.label}:</span>
                <span className="font-medium">{chip.value}</span>
                {onRemoveFilter && (
                  <button
                    type="button"
                    onClick={() => onRemoveFilter(chip.id)}
                    aria-label={`Remove filter ${chip.label}`}
                    className="text-text-tertiary hover:text-text-primary ml-0.5 cursor-pointer"
                  >
                    <X size={12} />
                  </button>
                )}
              </span>
            ))}
          </div>

          {filterActions && (
            <div className="flex items-center gap-2">
              {filterActions}
            </div>
          )}
        </div>
      )}

      {/* Table grid */}
      <div
        className="w-full overflow-x-auto focus-ring"
        tabIndex={0}
        role="region"
        aria-label="Data table container"
      >
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="h-10 bg-canvas border-b border-border-subtle">
              {columns.map(col => {
                const isSorted = sortKey === col.key;
                return (
                  <th
                    key={col.key}
                    scope="col"
                    style={{ width: col.width }}
                    onClick={() => col.sortable && handleSort(col.key)}
                    className={`px-4 text-[11px] font-medium tracking-[0.04em] uppercase text-text-tertiary select-none ${
                      col.align === 'right' || col.numeric ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'
                    } ${col.sortable ? 'cursor-pointer hover:text-text-primary transition-colors' : ''}`}
                  >
                    <div className={`inline-flex items-center gap-1 ${col.align === 'right' || col.numeric ? 'justify-end' : ''}`}>
                      <span>{col.header}</span>
                      {col.sortable && (
                        <span className="text-text-tertiary transition-transform duration-120">
                          {isSorted ? (
                            sortOrder === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                          ) : (
                            <ChevronDown size={14} className="opacity-0 group-hover:opacity-100" />
                          )}
                        </span>
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>

          <tbody className="divide-y divide-border-subtle">
            {loading ? (
              // Never more than 3 skeleton rows for a table
              Array.from({ length: 3 }).map((_, rIdx) => (
                <tr key={`skel-row-${rIdx}`} className={rowHeightClass}>
                  {columns.map((col, cIdx) => (
                    <td key={`skel-cell-${cIdx}`} className="px-4">
                      <Skeleton height={14} width={col.numeric ? 60 : cIdx === 0 ? 140 : 90} />
                    </td>
                  ))}
                </tr>
              ))
            ) : paginatedData.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="p-8 text-center">
                  {emptyState || (
                    <div className="flex flex-col items-center justify-center text-center p-6">
                      <Filter size={24} className="text-text-tertiary mb-2 stroke-[1.5]" />
                      <p className="text-[14px] font-medium text-text-primary">No records found</p>
                      <p className="text-[12px] text-text-secondary mt-1 max-w-sm">
                        No entries currently match the selected criteria.
                      </p>
                    </div>
                  )}
                </td>
              </tr>
            ) : (
              paginatedData.map((item, idx) => {
                const customHighlight = rowHighlight ? rowHighlight(item) : '';
                return (
                  <tr
                    key={rowKey(item)}
                    onClick={() => onRowClick && onRowClick(item)}
                    className={`${rowHeightClass} transition-colors duration-60 hover:bg-subtle ${
                      onRowClick ? 'cursor-pointer' : ''
                    } ${customHighlight}`}
                  >
                    {columns.map(col => (
                      <td
                        key={col.key}
                        className={`px-4 text-[13px] text-text-primary ${
                          col.numeric ? 'tabular text-right' : col.align === 'center' ? 'text-center' : col.align === 'right' ? 'text-right' : 'text-left'
                        }`}
                      >
                        {col.render(item, startIdx + idx)}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {!loading && data.length > pageSize && (
        <div className="flex items-center justify-between p-3 px-4 border-t border-border-subtle bg-canvas text-[12px] text-text-secondary">
          <div className="tabular">
            Showing <span className="font-medium text-text-primary">{startIdx + 1}</span>-
            <span className="font-medium text-text-primary">{Math.min(startIdx + pageSize, data.length)}</span> of{' '}
            <span className="font-medium text-text-primary">{data.length}</span>
          </div>

          <div className="flex items-center gap-1.5">
            <Button
              size="sm"
              variant="ghost"
              disabled={currentPage <= 1}
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              aria-label="Previous page"
            >
              <ChevronLeft size={14} />
            </Button>
            <span className="px-2 tabular font-medium text-text-primary">
              {currentPage} / {totalPages}
            </span>
            <Button
              size="sm"
              variant="ghost"
              disabled={currentPage >= totalPages}
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              aria-label="Next page"
            >
              <ChevronRight size={14} />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
