import React, { useEffect, useState } from 'react';
import { motion, useAnimation, useInView } from 'framer-motion';
import { useRef } from 'react';

const SettleApp = () => {
  const [activeStep, setActiveStep] = useState(0);
  const howItWorksRef = useRef(null);
  const isInView = useInView(howItWorksRef, { amount: 0.3 });
  
  const steps = [
    {
      title: "Connect Wallet",
      icon: "account_balance_wallet",
      description: "Link your Scroll-compatible wallet (MetaMask, Rabby) instantly. No setup fees, no registration forms.",
      color: "border-primary/20"
    },
    {
      title: "Generate Invoice",
      icon: "description",
      description: "Enter the amount in USDC and your client's address. We'll generate a professional, verifiable payment link.",
      color: "border-primary/30"
    },
    {
      title: "Get Paid",
      icon: "check_circle",
      description: "Your client pays in USDC, and we cover the gas costs behind the scenes. Funds land in your wallet instantly.",
      color: "border-primary/40"
    }
  ];

  useEffect(() => {
    if (isInView) {
      const interval = setInterval(() => {
        setActiveStep((prev) => (prev + 1) % steps.length);
      }, 3000);
      
      return () => clearInterval(interval);
    } else {
      setActiveStep(0);
    }
  }, [isInView, steps.length]);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
        delayChildren: 0.3
      }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        type: "spring",
        stiffness: 100,
        damping: 12
      }
    }
  };

  const stepVariants = {
    hidden: { y: 30, opacity: 0 },
    visible: (i) => ({
      y: 0,
      opacity: 1,
      transition: {
        delay: i * 0.15,
        duration: 0.5,
        ease: "easeOut"
      }
    })
  };

  return (
    <div className="bg-background-light dark:bg-background-dark text-[#1A1A1A] dark:text-white antialiased min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-primary/10 bg-background-light/80 dark:bg-background-dark/80 backdrop-blur-md">
        <div className="max-w-[1200px] mx-auto px-6 h-20 flex items-center justify-between">
          <motion.div 
            initial={{ x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="flex items-center gap-2 group cursor-pointer"
          >
            <div className="bg-primary p-1.5 rounded-full flex items-center justify-center">
              <svg className="size-6 text-white" fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
                <path d="M44 11.2727C44 14.0109 39.8386 16.3957 33.69 17.6364C39.8386 18.877 44 21.2618 44 24C44 26.7382 39.8386 29.123 33.69 30.3636C39.8386 31.6043 44 33.9891 44 36.7273C44 40.7439 35.0457 44 24 44C12.9543 44 4 40.7439 4 36.7273C4 33.9891 8.16144 31.6043 14.31 30.3636C8.16144 29.123 4 26.7382 4 24C4 21.2618 8.16144 18.877 14.31 17.6364C8.16144 16.3957 4 14.0109 4 11.2727C4 7.25611 12.9543 4 24 4C35.0457 4 44 7.25611 44 11.2727Z" fill="currentColor"></path>
              </svg>
            </div>
            <h1 className="text-2xl font-bold tracking-tighter text-primary">Settle</h1>
          </motion.div>
          
          <nav className="hidden md:flex items-center gap-10">
            <motion.a 
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="text-sm font-medium hover:text-primary transition-colors" 
              href="#how-it-works"
            >
              How it works
            </motion.a>
            <motion.a 
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="text-sm font-medium hover:text-primary transition-colors" 
              href="#freelancers"
            >
              For Freelancers
            </motion.a>
          </nav>
          
          <motion.div 
            initial={{ x: 20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="flex items-center gap-4"
          >
            <motion.button 
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="bg-primary hover:bg-primary/90 text-white text-sm font-bold px-6 py-2.5 rounded-full transition-all"
            >
              Connect Wallet
            </motion.button>
          </motion.div>
        </div>
      </header>

      {/* Main Content */}
      <main>
        {/* Hero Section */}
        <section className="min-h-[calc(100vh-5rem)] flex flex-col items-center justify-center text-center relative px-6 overflow-hidden">
          <div className="max-w-[1200px] mx-auto w-full">
            <motion.div 
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-bold uppercase tracking-wider mb-8 not-italic"
            >
              <span className="material-symbols-outlined text-sm">security</span>
              Secured by Scroll ZKP
            </motion.div>
            
            <motion.h1 
              initial={{ y: 30, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.7, delay: 0.2 }}
              className="text-4xl sm:text-5xl md:text-7xl font-bold leading-[1.1] tracking-tight max-w-[900px] mx-auto mb-8"
            >
              Send USDC Invoices. <br />
              <motion.span 
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, delay: 0.5 }}
                className="text-primary not-italic"
              >
                Pay Zero Gas.
              </motion.span>
            </motion.h1>
            
            <motion.p 
              initial={{ y: 30, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.7, delay: 0.4 }}
              className="text-base sm:text-lg md:text-xl text-gray-600 dark:text-gray-400 max-w-[650px] mx-auto mb-12 font-medium not-italic"
            >
              The first gasless invoicing protocol built on Scroll. 
              Get paid in full, instantly. Secured by zero-knowledge proofs.
            </motion.p>
            
            <motion.div 
              initial={{ y: 30, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.7, delay: 0.6 }}
              className="flex flex-col sm:flex-row gap-4 items-center justify-center w-full sm:w-auto"
            >
              <motion.button 
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="w-full sm:w-auto min-w-[200px] bg-primary text-white h-14 rounded-full font-bold text-lg hover:shadow-lg hover:shadow-primary/20 transition-all flex items-center justify-center gap-2"
              >
                Create Invoice
                <span className="material-symbols-outlined">arrow_forward</span>
              </motion.button>
              <motion.button 
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="w-full sm:w-auto min-w-[200px] bg-white dark:bg-white/10 border-2 border-[#1A1A1A] dark:border-white h-14 rounded-full font-bold text-lg hover:bg-gray-50 dark:hover:bg-white/20 transition-all"
              >
                Connect Wallet
              </motion.button>
            </motion.div>
          </div>
          
          <motion.div 
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 1, delay: 0.3 }}
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-4xl h-[600px] bg-gradient-to-b from-primary/5 to-transparent -z-10 blur-3xl rounded-full"
          ></motion.div>
        </section>

        {/* Features Section */}
        <section className="min-h-screen flex flex-col justify-center py-20 px-6">
          <div className="max-w-[1200px] mx-auto w-full">
            {/* Features Header */}
            <motion.div 
              initial={{ y: 20, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className="text-center mb-16"
            >
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-bold uppercase tracking-wider mb-4">
                <span className="material-symbols-outlined text-sm">star</span>
                Why Choose Settle
              </div>
              <h2 className="text-4xl md:text-5xl font-bold mb-4">Built for Modern Freelancers</h2>
              <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
                Experience the future of freelance payments with our zero-friction, gasless invoicing platform
              </p>
            </motion.div>

            <motion.div 
              variants={containerVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.2 }}
              className="grid grid-cols-1 md:grid-cols-3 gap-6"
            >
              {[
                {
                  icon: "money_off",
                  title: "0% Platform Fees",
                  description: "Transparency at its core. Keep every cent you earn without hidden infrastructure costs."
                },
                {
                  icon: "local_gas_station",
                  title: "Gasless Payments",
                  description: "We abstract the complexity of gas for you and your clients. No ETH required to settle bills."
                },
                {
                  icon: "bolt",
                  title: "Instant USDC",
                  description: "Near-instant finality for your hard-earned money using Scroll's high-speed ZKP layer."
                }
              ].map((feature, index) => (
                <motion.div 
                  key={index}
                  variants={itemVariants}
                  whileHover={{ y: -10, transition: { type: "spring", stiffness: 300 } }}
                  className="group p-8 md:p-10 rounded-xl bg-accent-light dark:bg-white/5 border border-primary/10 hover:border-primary/30 transition-all duration-300 h-full"
                >
                  <motion.div 
                    whileHover={{ rotate: 360 }}
                    transition={{ duration: 0.5 }}
                    className="size-12 md:size-14 bg-white dark:bg-white/10 rounded-full flex items-center justify-center text-primary mb-6 shadow-sm"
                  >
                    <span className="material-symbols-outlined text-2xl md:text-3xl">{feature.icon}</span>
                  </motion.div>
                  <h3 className="text-xl md:text-2xl font-bold mb-3">{feature.title}</h3>
                  <p className="text-gray-600 dark:text-gray-400 leading-relaxed font-medium text-sm md:text-base">
                    {feature.description}
                  </p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* How It Works Section - Redesigned */}
        <section ref={howItWorksRef} className="py-16 md:py-24 border-t border-primary/10 bg-gradient-to-b from-transparent via-primary/5 to-transparent" id="how-it-works">
          <div className="max-w-[1200px] mx-auto px-6">
            {/* Section Header */}
            <motion.div 
              initial={{ y: 20, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className="text-center mb-12 md:mb-20"
            >
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-bold uppercase tracking-wider mb-4">
                <span className="material-symbols-outlined text-sm">trending_flat</span>
                Simple Process
              </div>
              <h2 className="text-3xl md:text-5xl font-bold mb-4">How It Works</h2>
              <p className="text-base md:text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
                Get paid in three simple steps. No complexity, no gas fees, just instant payments.
              </p>
            </motion.div>
            
            {/* Steps Container */}
            <div className="relative max-w-5xl mx-auto">
              {/* Desktop: Horizontal connector line */}
              <div className="hidden md:block absolute top-20 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-primary/30 to-transparent"></div>
              
              {/* Steps Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-6">
                {steps.map((step, index) => (
                  <motion.div 
                    key={index}
                    custom={index}
                    variants={stepVariants}
                    initial="hidden"
                    whileInView="visible"
                    viewport={{ once: true, amount: 0.3 }}
                    className="relative"
                  >
                    {/* Mobile: Vertical connector */}
                    {index < steps.length - 1 && (
                      <div className="md:hidden absolute left-10 top-24 bottom-0 w-0.5 bg-gradient-to-b from-primary/30 to-transparent -mb-8"></div>
                    )}
                    
                    {/* Card */}
                    <motion.div
                      animate={isInView && activeStep === index ? {
                        scale: [1, 1.02, 1],
                        borderColor: ["rgba(236, 127, 19, 0.2)", "rgba(236, 127, 19, 0.5)", "rgba(236, 127, 19, 0.2)"]
                      } : {}}
                      transition={{ duration: 2, repeat: isInView && activeStep === index ? Infinity : 0 }}
                      className={`relative bg-white dark:bg-white/5 rounded-2xl p-6 md:p-8 border-2 ${step.color} transition-all duration-500 ${
                        activeStep === index ? 'shadow-xl shadow-primary/10' : 'shadow-md'
                      }`}
                    >
                      {/* Step Number Badge */}
                      <div className="absolute -top-4 -left-4 size-12 bg-primary text-white rounded-full flex items-center justify-center font-bold text-xl shadow-lg z-10">
                        {index + 1}
                      </div>
                      
                      {/* Icon Container */}
                      <div className="mb-6 flex justify-center md:justify-start">
                        <motion.div 
                          animate={activeStep === index ? { 
                            rotate: [0, 5, -5, 0],
                            scale: [1, 1.1, 1]
                          } : {}}
                          transition={{ duration: 0.5 }}
                          className={`relative size-16 md:size-20 rounded-2xl ${
                            index === steps.length - 1 ? 'bg-primary' : 'bg-primary/10'
                          } flex items-center justify-center`}
                        >
                          <span className={`material-symbols-outlined text-3xl md:text-4xl ${
                            index === steps.length - 1 ? 'text-white' : 'text-primary'
                          }`}>
                            {step.icon}
                          </span>
                          
                          {/* Active indicator */}
                          {activeStep === index && (
                            <motion.div
                              initial={{ scale: 0 }}
                              animate={{ scale: [1, 1.5, 1] }}
                              transition={{ duration: 1, repeat: Infinity }}
                              className="absolute inset-0 rounded-2xl border-2 border-primary/50"
                            ></motion.div>
                          )}
                        </motion.div>
                      </div>
                      
                      {/* Content */}
                      <div className="text-center md:text-left">
                        <h3 className="text-xl md:text-2xl font-bold mb-3">{step.title}</h3>
                        <p className="text-sm md:text-base text-gray-600 dark:text-gray-400 leading-relaxed">
                          {step.description}
                        </p>
                      </div>
                      
                      {/* Arrow for desktop */}
                      {index < steps.length - 1 && (
                        <div className="hidden md:block absolute -right-8 top-1/2 -translate-y-1/2 text-primary/30">
                          <span className="material-symbols-outlined text-5xl">arrow_forward</span>
                        </div>
                      )}
                    </motion.div>
                  </motion.div>
                ))}
              </div>
              
              {/* Progress Indicators */}
              <div className="flex justify-center items-center gap-3 mt-12">
                {steps.map((_, index) => (
                  <motion.button
                    key={index}
                    onClick={() => setActiveStep(index)}
                    className="group flex flex-col items-center gap-2"
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                  >
                    <motion.div
                      animate={{
                        scale: activeStep === index ? 1.2 : 1,
                        backgroundColor: activeStep === index 
                          ? "#ec7f13" 
                          : activeStep > index 
                            ? "#ec7f13" 
                            : "#d1d5db"
                      }}
                      transition={{ type: "spring", stiffness: 400 }}
                      className="size-3 rounded-full cursor-pointer"
                    />
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">
                      {index + 1}
                    </span>
                  </motion.button>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="my-20 md:my-24 p-8 md:p-20 rounded-xl bg-background-dark dark:bg-primary/10 text-white dark:text-white flex flex-col items-center text-center overflow-hidden relative mx-6">
          <div className="relative z-10 max-w-[1200px] mx-auto">
            <motion.h2 
              initial={{ y: 20, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              viewport={{ once: true }}
              className="text-3xl md:text-4xl lg:text-5xl font-bold mb-6"
            >
              Ready to settle your first invoice?
            </motion.h2>
            <motion.p 
              initial={{ y: 20, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
              className="text-base md:text-lg opacity-80 mb-8 md:mb-10 max-w-xl mx-auto"
            >
              Join thousands of freelancers getting paid on-chain without the complexity of gas management.
            </motion.p>
            <motion.button 
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="bg-primary hover:bg-primary/90 text-white px-8 md:px-10 py-3 md:py-4 rounded-full font-bold text-lg md:text-xl transition-all shadow-xl shadow-black/20"
            >
              Get Started Now
            </motion.button>
          </div>
          <motion.div 
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 0.2 }}
            viewport={{ once: true }}
            className="absolute inset-0 -z-0 pointer-events-none" 
            style={{ 
              backgroundImage: 'radial-gradient(circle at 20% 50%, #ec7f13 0%, transparent 50%), radial-gradient(circle at 80% 50%, #ec7f13 0%, transparent 50%)' 
            }}
          ></motion.div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-primary/10 py-12 mt-12 bg-accent-light/30 dark:bg-background-dark">
        <div className="max-w-[1200px] mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-6 md:gap-8">
          <motion.div 
            initial={{ x: -20, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1 }}
            viewport={{ once: true }}
            className="flex items-center gap-4"
          >
            <motion.div 
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="size-2 rounded-full bg-green-500"
            />
            <span className="text-sm font-medium opacity-70">Scroll Network: Operational</span>
          </motion.div>
          
          <motion.div 
            initial={{ y: 20, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            viewport={{ once: true }}
            className="flex flex-wrap items-center justify-center gap-4 md:gap-8 text-sm font-bold opacity-60"
          >
            {["Documentation", "Twitter", "Discord", "Github"].map((link, index) => (
              <motion.a
                key={index}
                whileHover={{ scale: 1.1, color: "#ec7f13" }}
                className="hover:text-primary transition-colors"
                href="#"
              >
                {link}
              </motion.a>
            ))}
          </motion.div>
          
          <motion.p 
            initial={{ x: 20, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1 }}
            viewport={{ once: true }}
            className="text-sm opacity-50 font-medium text-center md:text-left"
          >
            © 2026 Settle Protocol. Built on Scroll.
          </motion.p>
        </div>
      </footer>
    </div>
  );
};

export default SettleApp;