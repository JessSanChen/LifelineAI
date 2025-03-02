import { useEffect } from "react";

const DebugKeyListener = () => {
    useEffect(() => {
        const handleKeyPress = async (event: KeyboardEvent) => {
            if (event.key.toLowerCase() === "k") {
                try {
                    const response = await fetch("http://localhost:5001/debug");
                    const data = await response.json();
                    console.log("Debug response:", data);
                } catch (error) {
                    console.error("Error fetching debug endpoint:", error);
                }
            }
        };

        window.addEventListener("keydown", handleKeyPress);

        return () => {
            window.removeEventListener("keydown", handleKeyPress);
        };
    }, []);

    return null; // This component does not render anything
};

export default DebugKeyListener;