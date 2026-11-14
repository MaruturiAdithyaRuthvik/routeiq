import { useId, useState, type ReactNode } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { CalendarDays, Check, ChevronRight } from "lucide-react"
import { format } from "date-fns"
import type { DateRange } from "react-day-picker"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import {
    Command,
    CommandDialog,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
    CommandShortcut,
} from "@/components/ui/command"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"

export { Button }
export {
    Card,
    CardAction,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
export { Input } from "@/components/ui/input"
export {
    Select,
    SelectContent,
    SelectGroup,
    SelectItem,
    SelectLabel,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
export { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
export {
    Dialog,
    DialogClose,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"
export {
    Sheet,
    SheetClose,
    SheetContent,
    SheetDescription,
    SheetFooter,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet"
export {
    Table,
    TableBody,
    TableCaption,
    TableCell,
    TableFooter,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
export { Skeleton } from "@/components/ui/skeleton"
export {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip"

export interface SegmentOption<T extends string> {
    value: T
    label: string
    icon?: ReactNode
}

export function Segmented<T extends string>({
    options,
    value,
    onChange,
    label,
    className = "",
}: {
    options: SegmentOption<T>[]
    value: T
    onChange: (value: T) => void
    label: string
    className?: string
}) {
    const id = useId()
    return (
        <div
            role="group"
            aria-label={label}
            className={`segmented-control ${className}`}
        >
            {options.map((option) => (
                <button
                    key={option.value}
                    type="button"
                    aria-pressed={value === option.value}
                    className="segmented-option"
                    onClick={() => onChange(option.value)}
                >
                    {value === option.value && (
                        <motion.span
                            layoutId={`segmented-thumb-${id}`}
                            className="segmented-thumb"
                            transition={{
                                type: "spring",
                                stiffness: 300,
                                damping: 30,
                            }}
                        />
                    )}
                    <span className="segmented-label">
                        {option.icon}
                        {option.label}
                    </span>
                </button>
            ))}
        </div>
    )
}

const toneByStatus: Record<string, string> = {
    APPROVED: "status-success",
    PAID: "status-success",
    REIMBURSED: "status-success",
    COMPLETED: "status-success",
    PENDING: "status-warning",
    PENDING_APPROVAL: "status-warning",
    SCHEDULED: "status-info",
    OPEN: "status-danger",
    REJECTED: "status-danger",
    CANCELLED: "status-neutral",
    RESOLVED: "status-success",
    DISMISSED: "status-neutral",
}

export function StatusPill({ status }: { status: string }) {
    return (
        <span
            className={`status-pill ${toneByStatus[status] ?? "status-neutral"}`}
        >
            {status.replaceAll("_", " ").toLowerCase()}
        </span>
    )
}

export function DateRangePicker({
    value,
    onChange,
    holidays = [],
    label = "Date range",
}: {
    value?: DateRange
    onChange: (range: DateRange | undefined) => void
    holidays?: Date[]
    label?: string
}) {
    const [open, setOpen] = useState(false)
    const description =
        value?.from && value.to
            ? `${format(value.from, "MMM d")} – ${format(value.to, "MMM d, yyyy")}`
            : value?.from
              ? format(value.from, "MMM d, yyyy")
              : "Choose dates"

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button
                    variant="outline"
                    className="min-w-52 justify-start gap-2 text-left font-normal"
                    aria-label={label}
                >
                    <CalendarDays className="text-muted-foreground" />
                    <span>{description}</span>
                </Button>
            </PopoverTrigger>
            <PopoverContent
                align="start"
                className="frosted w-auto rounded-[24px] p-3 shadow-xl"
            >
                <Calendar
                    mode="range"
                    selected={value}
                    onSelect={onChange}
                    numberOfMonths={1}
                    modifiers={{
                        weekend: { dayOfWeek: [0, 6] },
                        holiday: holidays,
                    }}
                    modifiersClassNames={{
                        weekend: "day-weekend",
                        holiday: "day-holiday",
                    }}
                />
                <div className="border-border text-muted-foreground flex items-center gap-4 border-t px-2 pt-3 text-xs">
                    <span className="flex items-center gap-1.5">
                        <i className="bg-muted-foreground/50 size-2 rounded-full" />
                        Weekend
                    </span>
                    <span className="flex items-center gap-1.5">
                        <i className="bg-danger size-2 rounded-full" />
                        Holiday
                    </span>
                </div>
            </PopoverContent>
        </Popover>
    )
}

export function Ring({
    value,
    size = 56,
    stroke = 5,
    label,
}: {
    value: number
    size?: number
    stroke?: number
    label: string
}) {
    const radius = (size - stroke) / 2
    const circumference = 2 * Math.PI * radius
    const clampedValue = Math.min(100, Math.max(0, value))
    return (
        <svg
            width={size}
            height={size}
            viewBox={`0 0 ${size} ${size}`}
            role="img"
            aria-label={`${label}: ${clampedValue}%`}
            className="shrink-0 -rotate-90"
        >
            <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke="var(--grouped)"
                strokeWidth={stroke}
            />
            <motion.circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke="var(--primary)"
                strokeWidth={stroke}
                strokeLinecap="round"
                strokeDasharray={circumference}
                initial={{ strokeDashoffset: circumference }}
                animate={{
                    strokeDashoffset: circumference * (1 - clampedValue / 100),
                }}
                transition={{ duration: 0.8, ease: [0.28, 0.11, 0.32, 1] }}
            />
        </svg>
    )
}

export function Gauge({
    value,
    label,
    caption,
}: {
    value: number
    label: string
    caption?: string
}) {
    const clampedValue = Math.min(100, Math.max(0, value))
    return (
        <div
            className="gauge"
            role="img"
            aria-label={`${label} ${clampedValue}%`}
        >
            <svg viewBox="0 0 160 90" aria-hidden="true">
                <path
                    d="M 18 80 A 62 62 0 0 1 142 80"
                    fill="none"
                    stroke="var(--grouped)"
                    strokeWidth="12"
                    strokeLinecap="round"
                />
                <motion.path
                    d="M 18 80 A 62 62 0 0 1 142 80"
                    fill="none"
                    stroke="var(--primary)"
                    strokeWidth="12"
                    strokeLinecap="round"
                    pathLength="100"
                    initial={{ strokeDasharray: "0 100" }}
                    animate={{ strokeDasharray: `${clampedValue} 100` }}
                    transition={{ duration: 0.8, ease: [0.28, 0.11, 0.32, 1] }}
                />
            </svg>
            <div className="gauge-copy">
                <strong className="tabular-nums">{clampedValue}%</strong>
                <span>{label}</span>
                {caption && <small>{caption}</small>}
            </div>
        </div>
    )
}

export function Stepper({
    steps,
    currentStep,
}: {
    steps: string[]
    currentStep: number
}) {
    return (
        <ol className="stepper">
            {steps.map((step, index) => {
                const complete = index < currentStep
                const active = index === currentStep
                return (
                    <li
                        key={step}
                        className={`stepper-item${complete ? "is-complete" : ""}${active ? "is-active" : ""}`}
                        aria-current={active ? "step" : undefined}
                    >
                        <span className="stepper-marker">
                            {complete ? <Check size={14} /> : index + 1}
                        </span>
                        <span>{step}</span>
                        {index < steps.length - 1 && (
                            <span className="stepper-line" />
                        )}
                    </li>
                )
            })}
        </ol>
    )
}

export interface TimelineEntry {
    title: string
    detail: string
    date: string
    tone?: "blue" | "green" | "amber"
}

export function Timeline({ items }: { items: TimelineEntry[] }) {
    return (
        <ol className="timeline">
            {items.map((item, index) => (
                <li
                    key={`${item.title}-${item.date}`}
                    className="timeline-item"
                >
                    <span
                        className={`timeline-dot tone-${item.tone ?? "blue"}`}
                    />
                    {index < items.length - 1 && (
                        <span className="timeline-line" />
                    )}
                    <div className="timeline-copy">
                        <div className="flex items-start justify-between gap-4">
                            <strong>{item.title}</strong>
                            <time className="tabular-nums">{item.date}</time>
                        </div>
                        <p>{item.detail}</p>
                    </div>
                </li>
            ))}
        </ol>
    )
}

export interface PaletteItem {
    label: string
    description?: string
    shortcut?: string
    icon?: ReactNode
    onSelect: () => void
    group?: string
}

export function CommandPalette({
    open,
    onOpenChange,
    items,
}: {
    open: boolean
    onOpenChange: (open: boolean) => void
    items: PaletteItem[]
}) {
    const groups = [...new Set(items.map((item) => item.group ?? "Navigate"))]
    return (
        <CommandDialog
            open={open}
            onOpenChange={onOpenChange}
            title="Quick navigation"
            description="Search pages and actions."
            className="frosted border-border max-w-xl rounded-[28px] border p-2 shadow-2xl"
        >
            <Command className="bg-transparent">
                <CommandInput
                    placeholder="Search pages, people, or actions…"
                    className="h-12 text-base"
                />
                <CommandList className="max-h-[min(60vh,480px)] p-1">
                    <CommandEmpty className="text-muted-foreground py-12">
                        No results found.
                    </CommandEmpty>
                    {groups.map((group) => (
                        <CommandGroup key={group} heading={group}>
                            {items
                                .filter(
                                    (item) =>
                                        (item.group ?? "Navigate") === group,
                                )
                                .map((item) => (
                                    <CommandItem
                                        key={item.label}
                                        value={`${item.label} ${item.description ?? ""}`}
                                        onSelect={() => {
                                            item.onSelect()
                                            onOpenChange(false)
                                        }}
                                        className="min-h-12 rounded-xl px-3"
                                    >
                                        {item.icon}
                                        <span className="flex min-w-0 flex-col">
                                            <span>{item.label}</span>
                                            {item.description && (
                                                <span className="text-muted-foreground text-xs">
                                                    {item.description}
                                                </span>
                                            )}
                                        </span>
                                        {item.shortcut && (
                                            <CommandShortcut>
                                                {item.shortcut}
                                            </CommandShortcut>
                                        )}
                                        <ChevronRight className="ml-auto size-4 opacity-40" />
                                    </CommandItem>
                                ))}
                        </CommandGroup>
                    ))}
                </CommandList>
            </Command>
        </CommandDialog>
    )
}

export function Reveal({
    children,
    className,
    delay = 0,
}: {
    children: ReactNode
    className?: string
    delay?: number
}) {
    return (
        <AnimatePresence>
            <motion.div
                className={className}
                initial={{ opacity: 0, y: 12, filter: "blur(6px)" }}
                whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{
                    duration: 0.55,
                    delay,
                    ease: [0.28, 0.11, 0.32, 1],
                }}
            >
                {children}
            </motion.div>
        </AnimatePresence>
    )
}
