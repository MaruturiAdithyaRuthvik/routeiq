import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
    type ReactNode,
} from "react"

type ThemeChoice = "light" | "dark" | "system"
interface ThemeContextValue {
    theme: "light" | "dark"
    toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

function initialChoice(): ThemeChoice {
    if (typeof window === "undefined") return "system"
    const choice = window.localStorage.getItem("routeiq.theme")
    return choice === "light" || choice === "dark" ? choice : "system"
}

export function ThemeProvider({ children }: { children: ReactNode }) {
    const [choice, setChoice] = useState<ThemeChoice>(initialChoice)
    const [systemDark, setSystemDark] = useState(false)

    useEffect(() => {
        const media = window.matchMedia("(prefers-color-scheme: dark)")
        const update = () => setSystemDark(media.matches)
        update()
        media.addEventListener("change", update)
        return () => media.removeEventListener("change", update)
    }, [])

    const theme = choice === "system" ? (systemDark ? "dark" : "light") : choice

    useEffect(() => {
        document.documentElement.classList.toggle("dark", theme === "dark")
        document.documentElement.dataset.theme = theme
    }, [theme])

    const toggleTheme = useCallback(() => {
        const next = theme === "dark" ? "light" : "dark"
        window.localStorage.setItem("routeiq.theme", next)
        setChoice(next)
    }, [theme])

    const value = useMemo(() => ({ theme, toggleTheme }), [theme, toggleTheme])
    return (
        <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
    )
}

export function useTheme(): ThemeContextValue {
    const context = useContext(ThemeContext)
    if (!context) throw new Error("useTheme must be used within ThemeProvider.")
    return context
}
