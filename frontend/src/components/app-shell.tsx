import { useEffect, useMemo, useState } from "react"
import {
    Activity,
    BarChart3,
    CalendarDays,
    ChevronDown,
    ClipboardCheck,
    Command as CommandIcon,
    Database,
    FileText,
    Home,
    Moon,
    ReceiptText,
    Settings2,
    ShieldCheck,
    Sun,
    Users,
    WalletCards,
} from "lucide-react"
import {
    Link,
    NavLink,
    Outlet,
    useLocation,
    useNavigate,
} from "react-router-dom"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"
import { Dock, DockIcon } from "@/components/ui/dock"
import {
    Button,
    CommandPalette,
    Segmented,
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/primitives"
import type { PaletteItem } from "@/components/ui/primitives"
import { useAuth } from "@/providers/auth-provider"
import { useTheme } from "@/providers/theme-provider"
import { SystemRole, type AuthPersona } from "@/api/types"

interface NavigationItem {
    label: string
    to: string
    icon: typeof Home
    roles?: SystemRole[]
}

const navigation: NavigationItem[] = [
    { label: "Overview", to: "/", icon: Home },
    { label: "My requests", to: "/leave-requests", icon: FileText },
    {
        label: "Leave",
        to: "/leave",
        icon: CalendarDays,
        roles: [
            SystemRole.REQUESTER,
            SystemRole.PROCESS_OWNER,
            SystemRole.ADMIN,
        ],
    },
    { label: "Expenses", to: "/expense-claims", icon: ReceiptText },
    {
        label: "Approvals",
        to: "/approvals/inbox",
        icon: ClipboardCheck,
        roles: [
            SystemRole.APPROVER,
            SystemRole.PROCESS_OWNER,
            SystemRole.ADMIN,
        ],
    },
    {
        label: "Reimbursements",
        to: "/reimbursements",
        icon: WalletCards,
        roles: [
            SystemRole.REQUESTER,
            SystemRole.PROCESS_OWNER,
            SystemRole.ANALYST,
            SystemRole.ADMIN,
        ],
    },
    {
        label: "Analytics",
        to: "/metrics/overview",
        icon: BarChart3,
        roles: [SystemRole.PROCESS_OWNER, SystemRole.ANALYST, SystemRole.ADMIN],
    },
    {
        label: "Audit",
        to: "/audit/findings",
        icon: ShieldCheck,
        roles: [SystemRole.PROCESS_OWNER, SystemRole.ANALYST, SystemRole.ADMIN],
    },
    {
        label: "Employees",
        to: "/employees",
        icon: Users,
        roles: [SystemRole.PROCESS_OWNER, SystemRole.ADMIN],
    },
    {
        label: "Policies",
        to: "/leave-policies",
        icon: Settings2,
        roles: [SystemRole.PROCESS_OWNER, SystemRole.ANALYST, SystemRole.ADMIN],
    },
    {
        label: "Evaluation",
        to: "/evaluation/summary",
        icon: Activity,
        roles: [SystemRole.ANALYST, SystemRole.ADMIN],
    },
    {
        label: "Dataset",
        to: "/dataset/manifest",
        icon: Database,
        roles: [SystemRole.PROCESS_OWNER, SystemRole.ANALYST, SystemRole.ADMIN],
    },
]

const roleLabels: Record<AuthPersona["system_role"], string> = {
    [SystemRole.REQUESTER]: "Requester",
    [SystemRole.APPROVER]: "Approver",
    [SystemRole.PROCESS_OWNER]: "Process owner",
    [SystemRole.ANALYST]: "Operations analyst",
    [SystemRole.ADMIN]: "System administrator",
}

function initials(name: string): string {
    return name
        .split(" ")
        .map((part) => part[0] ?? "")
        .join("")
        .slice(0, 2)
        .toUpperCase()
}

function visibleNavigation(role: SystemRole): NavigationItem[] {
    return navigation.filter((item) => !item.roles || item.roles.includes(role))
}

function PersonaSwitcher() {
    const { personas, persona, selectPersona } = useAuth()
    const options = useMemo(
        () =>
            personas.map((actor) => ({
                value: actor.employee_id,
                label: "",
                icon: (
                    <>
                        <Avatar className="border-border size-8 border">
                            <AvatarFallback className="bg-secondary text-[10px] font-semibold">
                                {initials(actor.display_name)}
                            </AvatarFallback>
                        </Avatar>
                        <span className="persona-chip-copy">
                            <strong>{actor.display_name.split(" ")[0]}</strong>
                            <span>{roleLabels[actor.system_role]}</span>
                        </span>
                    </>
                ),
            })),
        [personas],
    )

    if (!persona) return null

    return (
        <Popover>
            <PopoverTrigger asChild>
                <button
                    type="button"
                    className="persona-trigger"
                    aria-label={`Current persona: ${persona.display_name}, ${roleLabels[persona.system_role]}`}
                >
                    <Avatar className="size-7">
                        <AvatarFallback className="bg-primary/10 text-primary text-[10px] font-semibold">
                            {initials(persona.display_name)}
                        </AvatarFallback>
                    </Avatar>
                    <span className="persona-name">{persona.display_name}</span>
                    <span className="persona-role">
                        {roleLabels[persona.system_role]}
                    </span>
                    <ChevronDown size={13} aria-hidden="true" />
                </button>
            </PopoverTrigger>
            <PopoverContent align="end" className="frosted persona-content">
                <div>
                    <p className="text-sm font-semibold">Switch persona</p>
                    <p className="text-muted-foreground mt-1 text-xs">
                        Preview RouteIQ from each role.
                    </p>
                </div>
                <Segmented
                    label="Available personas"
                    value={persona.employee_id}
                    onChange={selectPersona}
                    options={options}
                    className="persona-grid w-full"
                />
                <p className="text-muted-foreground text-[11px]">
                    Demo identities only. Permissions follow the selected role.
                </p>
            </PopoverContent>
        </Popover>
    )
}

function AppearanceButton() {
    const { theme, toggleTheme } = useTheme()
    return (
        <Tooltip>
            <TooltipTrigger asChild>
                <Button
                    variant="ghost"
                    size="icon"
                    className="top-icon-button"
                    onClick={toggleTheme}
                    aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
                >
                    {theme === "dark" ? (
                        <Sun strokeWidth={1.5} />
                    ) : (
                        <Moon strokeWidth={1.5} />
                    )}
                </Button>
            </TooltipTrigger>
            <TooltipContent>Appearance</TooltipContent>
        </Tooltip>
    )
}

function RouteSkeleton() {
    return (
        <div className="page-stack" aria-label="Loading RouteIQ" role="status">
            <div className="space-y-3">
                <div className="skeleton-line bg-muted w-24" />
                <div className="skeleton-line bg-muted h-12 w-2/3" />
                <div className="skeleton-line bg-muted w-1/2" />
            </div>
            <div className="grid gap-4 md:grid-cols-3">
                {[0, 1, 2].map((item) => (
                    <div
                        key={item}
                        className="bg-grouped h-36 animate-pulse rounded-[24px]"
                    />
                ))}
            </div>
            <span className="sr-only">Loading your workspace…</span>
        </div>
    )
}

export function AppShell() {
    const { persona, ready, error, retry } = useAuth()
    const { theme, toggleTheme } = useTheme()
    const navigate = useNavigate()
    const location = useLocation()
    const [paletteOpen, setPaletteOpen] = useState(false)
    const role = persona?.system_role ?? SystemRole.REQUESTER
    const items = visibleNavigation(role)
    const paletteItems: PaletteItem[] = useMemo(
        () => [
            ...items.map((item) => ({
                label: item.label,
                description: item.to === "/" ? "Your workspace" : item.to,
                icon: <item.icon size={16} strokeWidth={1.5} />,
                onSelect: () => navigate(item.to),
            })),
            {
                label: "Switch appearance",
                description: `Currently ${theme}`,
                icon: theme === "dark" ? <Sun size={16} /> : <Moon size={16} />,
                onSelect: toggleTheme,
                group: "Actions",
            },
        ],
        [items, navigate, theme, toggleTheme],
    )

    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (
                (event.metaKey || event.ctrlKey) &&
                event.key.toLowerCase() === "k"
            ) {
                event.preventDefault()
                setPaletteOpen((open) => !open)
            }
            if (event.key === "Escape") setPaletteOpen(false)
        }
        window.addEventListener("keydown", handleKeyDown)
        return () => window.removeEventListener("keydown", handleKeyDown)
    }, [])

    if (!ready) {
        return (
            <div className="app-shell">
                <header className="top-bar frosted">
                    <Link to="/" className="brand">
                        <span className="brand-mark">R</span>
                        RouteIQ
                    </Link>
                </header>
                <main className="app-main">
                    {error ? (
                        <div className="state-card" role="alert">
                            <ShieldCheck className="text-danger mx-auto size-8" />
                            <h2>We couldn’t open your workspace</h2>
                            <p>{error.message}</p>
                            <Button className="mt-5" onClick={retry}>
                                Try again
                            </Button>
                        </div>
                    ) : (
                        <RouteSkeleton />
                    )}
                </main>
            </div>
        )
    }

    return (
        <div className="app-shell">
            <header className="top-bar frosted">
                <Link to="/" className="brand" aria-label="RouteIQ home">
                    <span className="brand-mark">R</span>
                    RouteIQ
                </Link>
                <div className="top-actions">
                    <PersonaSwitcher />
                    <AppearanceButton />
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="top-icon-button"
                                aria-label="Open command palette"
                                onClick={() => setPaletteOpen(true)}
                            >
                                <CommandIcon strokeWidth={1.5} />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>Quick search · ⌘K</TooltipContent>
                    </Tooltip>
                </div>
            </header>
            <main className="app-main" key={location.pathname}>
                <Outlet />
            </main>
            <div className="route-dock-wrap" aria-label="Primary navigation">
                <Dock
                    className="route-dock"
                    iconSize={44}
                    iconMagnification={49}
                    iconDistance={115}
                >
                    {items.map((item) => (
                        <DockIcon key={item.to} className="p-0">
                            <NavLink
                                to={item.to}
                                end={item.to === "/"}
                                className="dock-link"
                                aria-label={item.label}
                                title={item.label}
                            >
                                <item.icon size={20} strokeWidth={1.5} />
                            </NavLink>
                        </DockIcon>
                    ))}
                </Dock>
            </div>
            <nav
                className="mobile-tabs frosted"
                aria-label="Primary navigation"
            >
                {items.slice(0, 4).map((item) => (
                    <NavLink
                        key={item.to}
                        to={item.to}
                        end={item.to === "/"}
                        className="mobile-tab"
                        aria-label={item.label}
                    >
                        <item.icon aria-hidden="true" />
                        <span>{item.label}</span>
                    </NavLink>
                ))}
            </nav>
            <CommandPalette
                open={paletteOpen}
                onOpenChange={setPaletteOpen}
                items={paletteItems}
            />
        </div>
    )
}
