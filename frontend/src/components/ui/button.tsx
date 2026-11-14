import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { Slot } from "radix-ui"

export const buttonVariants = cva(
    "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-medium transition-[background,color,transform,box-shadow] duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 active:scale-[.98] [&_svg]:size-4 [&_svg]:shrink-0",
    {
        variants: {
            variant: {
                default:
                    "bg-primary text-white shadow-sm hover:bg-[var(--primary-hover)]",
                secondary:
                    "bg-secondary text-secondary-foreground hover:bg-[color-mix(in_srgb,var(--grouped),var(--foreground)_5%)]",
                outline:
                    "border border-border bg-transparent text-foreground hover:bg-secondary",
                ghost: "text-foreground hover:bg-secondary",
                destructive: "bg-danger/10 text-danger hover:bg-danger/15",
                link: "gap-1 rounded-none p-0 text-primary hover:text-[var(--primary-hover)]",
            },
            size: {
                default: "h-10 px-5",
                sm: "h-9 px-4 text-[13px]",
                lg: "h-12 px-6 text-[15px]",
                icon: "size-10 p-0",
                "icon-sm": "size-8 p-0",
                "icon-lg": "size-12 p-0",
                xs: "h-7 px-3 text-xs",
            },
        },
        defaultVariants: {
            variant: "default",
            size: "default",
        },
    },
)

type ButtonProps = React.ComponentPropsWithoutRef<"button"> &
    VariantProps<typeof buttonVariants> & { asChild?: boolean }

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    (
        { className, variant = "default", size = "default", asChild, ...props },
        ref,
    ) => {
        const Component = asChild ? Slot.Root : "button"
        return (
            <Component
                ref={ref}
                data-slot="button"
                data-variant={variant}
                data-size={size}
                className={cn(buttonVariants({ variant, size, className }))}
                {...props}
            />
        )
    },
)

Button.displayName = "Button"

export { Button }
