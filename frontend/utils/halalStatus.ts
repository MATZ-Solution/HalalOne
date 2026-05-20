export const statusBadge = (status: string) => {
    switch (status?.toLowerCase()) {
        case "halal":
            return "bg-green-500/10 text-green-400 border border-green-500/25"
        case "haram":
            return "bg-red-500/10 text-red-400 border border-red-500/25"
        default:
            return "bg-yellow-500/10 text-yellow-400 border border-yellow-500/25"
    }
}

export const statusAccent = (status: string) => {
    switch (status?.toLowerCase()) {
        case "halal":
            return "bg-green-500"
        case "haram":
            return "bg-red-500"
        default:
            return "bg-yellow-500"
    }
}

export const statusDot = (status: string) => {
    switch (status?.toLowerCase()) {
        case "halal":
            return "bg-green-400"
        case "haram":
            return "bg-red-400"
        default:
            return "bg-yellow-400"
    }
}
