"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import AuthDialog from "./AuthDialog";
import { Menu, X, Home, Target, Presentation, TrendingUp, Search, BarChart3, Globe, Bot, Youtube } from "lucide-react";

const links = [
  { href: "/", label: "Home", icon: Home },
  { href: "/market_analysis", label: "Market Analysis", icon: BarChart3 },
  { href: "/ai_researcher_agent", label: "AI Researcher", icon: Bot },
  { href: "/ai_pitch_deck_builder", label: "AI Pitch Deck Builder", icon: Presentation },
  { href: "/tube_gen", label: "TubeGen AI", icon: Youtube },
  { href: "/funding_trends", label: "Funding Trends", icon: TrendingUp },
  { href: "/mvp_builder", label: "MVP Builder", icon: Globe },
];

function ElegantShape({
    className,
    delay = 0,
    width = 200,
    height = 50,
    rotate = 0,
    gradient = "from-white/[0.08]",
}: {
    className?: string;
    delay?: number;
    width?: number;
    height?: number;
    rotate?: number;
    gradient?: string;
}) {
    return (
        <motion.div
            initial={{
                opacity: 0,
                y: -50,
                rotate: rotate - 10,
            }}
            animate={{
                opacity: 1,
                y: 0,
                rotate: rotate,
            }}
            transition={{
                duration: 2,
                delay,
                ease: [0.23, 0.86, 0.39, 0.96],
                opacity: { duration: 1 },
            }}
            className={`absolute ${className}`}
        >
            <motion.div
                animate={{
                    y: [0, 8, 0],
                }}
                transition={{
                    duration: 8,
                    repeat: Number.POSITIVE_INFINITY,
                    ease: "easeInOut",
                }}
                style={{
                    width,
                    height,
                }}
                className="relative"
            >
                <div
                    className={`absolute inset-0 rounded-full bg-gradient-to-r to-transparent ${gradient} backdrop-blur-[1px] border border-white/[0.1] shadow-[0_4px_16px_0_rgba(255,255,255,0.05)]`}
                />
            </motion.div>
        </motion.div>
    );
}

export default function Navbar() {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <motion.nav
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.6, ease: [0.25, 0.4, 0.25, 1] }}
      className={`sticky top-0 z-50 transition-all duration-300 overflow-hidden ${
        scrolled
          ? "bg-[#030303]/90 backdrop-blur-xl border-b border-white/[0.08] shadow-[0_8px_32px_rgba(0,0,0,0.4)]"
          : "bg-[#030303]/60 backdrop-blur-lg border-b border-white/[0.05]"
      }`}
    >
      {/* Background gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/[0.03] via-transparent to-rose-500/[0.03] blur-2xl" />
      
      {/* Floating geometric shapes */}
      <div className="absolute inset-0 overflow-hidden">
        <ElegantShape
          delay={0.1}
          width={120}
          height={30}
          rotate={15}
          gradient="from-indigo-500/[0.08]"
          className="left-[5%] top-1/2"
        />
        <ElegantShape
          delay={0.2}
          width={80}
          height={20}
          rotate={-20}
          gradient="from-rose-500/[0.08]"
          className="right-[15%] top-1/3"
        />
        <ElegantShape
          delay={0.3}
          width={100}
          height={25}
          rotate={10}
          gradient="from-violet-500/[0.08]"
          className="left-[25%] top-1/4"
        />
        <ElegantShape
          delay={0.4}
          width={60}
          height={15}
          rotate={-15}
          gradient="from-amber-500/[0.08]"
          className="right-[5%] top-1/2"
        />
      </div>

      <div className="relative z-10 mx-auto max-w-7xl px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Left side: Logo */}
          <div className="flex-shrink-0">
            <Link href="/" className="group">
              <motion.div
                whileHover={{ scale: 1.05 }}
                className="flex items-center gap-2 font-bold text-xl bg-clip-text text-transparent bg-gradient-to-r from-white via-blue-100 to-purple-100 leading-none"
              >
                Founder Assistant AI
              </motion.div>
            </Link>
          </div>

                      {/* Center: Desktop Navigation */}
            <div className="hidden xl:flex items-center justify-center flex-1">
              <ul className="flex items-center gap-2">
                {links.map((l, index) => {
                  const active =
                    pathname === l.href ||
                    (l.href !== "/" && pathname.startsWith(l.href));
                  const IconComponent = l.icon;
                  return (
                    <motion.li
                      key={l.href}
                      initial={{ opacity: 0, y: -20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5, delay: index * 0.1 }}
                      className="flex items-center"
                    >
                      <Link
                        href={l.href}
                        className={`relative px-3 py-2 rounded-xl text-sm font-medium transition-all duration-300 group flex items-center gap-2 justify-center min-h-[32px] ${
                          active
                            ? "text-white"
                            : "text-white/70 hover:text-white"
                        }`}
                      >
                        {active && (
                          <motion.div
                            layoutId="activeTab"
                            className="absolute inset-0 bg-white/[0.08] rounded-xl border border-white/[0.15] backdrop-blur-sm"
                            initial={false}
                            transition={{ type: "spring", stiffness: 500, damping: 30 }}
                          />
                        )}
                        <IconComponent className="relative z-10 w-4 h-4" />
                        <span className="relative z-10 whitespace-nowrap">{l.label}</span>
                      </Link>
                    </motion.li>
                  );
                })}
              </ul>
            </div>

          {/* Right side: Auth buttons */}
          <div className="flex items-center gap-3 flex-shrink-0">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <AuthDialog />
            </motion.div>

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="xl:hidden p-2 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white/80 hover:bg-white/[0.1] transition-all duration-300"
            >
              {mobileMenuOpen ? (
                <X className="w-5 h-5" />
              ) : (
                <Menu className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        <AnimatePresence>
          {mobileMenuOpen && (
                         <motion.div
               initial={{ opacity: 0, height: 0 }}
               animate={{ opacity: 1, height: "auto" }}
               exit={{ opacity: 0, height: 0 }}
               transition={{ duration: 0.3, ease: "easeInOut" }}
               className="xl:hidden overflow-hidden"
             >
                             <div className="py-4 space-y-2">
                 {links.map((l, index) => {
                   const active =
                     pathname === l.href ||
                     (l.href !== "/" && pathname.startsWith(l.href));
                   const IconComponent = l.icon;
                   return (
                     <motion.div
                       key={l.href}
                       initial={{ opacity: 0, x: -20 }}
                       animate={{ opacity: 1, x: 0 }}
                       transition={{ duration: 0.3, delay: index * 0.1 }}
                     >
                       <Link
                         href={l.href}
                         onClick={() => setMobileMenuOpen(false)}
                         className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
                           active
                             ? "bg-white/[0.08] text-white border border-white/[0.15]"
                             : "text-white/70 hover:bg-white/[0.05] hover:text-white"
                         }`}
                       >
                         <IconComponent className="w-4 h-4" />
                         {l.label}
                       </Link>
                     </motion.div>
                   );
                 })}
               </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.nav>
  );
}