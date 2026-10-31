"use client";

import React, { useState, useMemo } from "react";
import {
  TrendingUp,
  Target,
  Sliders,
  AlertCircle,
  ShieldCheck,
  CheckCircle2,
  PieChart,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";

interface SipCalculatorViewProps {
  initialMonthly?: number;
  initialYears?: number;
  initialReturn?: number;
}

export const SipCalculatorView: React.FC<SipCalculatorViewProps> = ({
  initialMonthly = 5000,
  initialYears = 5,
  initialReturn = 12,
}) => {
  const [goal, setGoal] = useState<string>("Wealth Creation");
  const [monthlyInvestment, setMonthlyInvestment] = useState<number>(initialMonthly);
  const [durationYears, setDurationYears] = useState<number>(initialYears);
  const [expectedReturn, setExpectedReturn] = useState<number>(initialReturn);

  // Mock surplus calculation from customer history
  const mockMonthlyIncome = 85000;
  const mockExistingExpenses = 35000;
  const monthlySurplus = mockMonthlyIncome - mockExistingExpenses; // ₹50,000
  const surplusUtilizationPct = Math.round((monthlyInvestment / monthlySurplus) * 100);
  const isSurplusSafe = monthlyInvestment <= monthlySurplus;

  // Compute year-by-year compounding data for Recharts (Navy #002E6E and Blue #00BAF2 only!)
  const chartData = useMemo(() => {
    const data = [];
    const monthlyRate = expectedReturn / (12 * 100);

    for (let yr = 1; yr <= durationYears; yr++) {
      const months = yr * 12;
      const invested = monthlyInvestment * months;
      let fv = invested;
      if (expectedReturn > 0) {
        const cf = Math.pow(1 + monthlyRate, months);
        fv = monthlyInvestment * ((cf - 1) / monthlyRate) * (1 + monthlyRate);
      }
      data.push({
        year: `Yr ${yr}`,
        investedAmount: Math.round(invested),
        projectedCorpus: Math.round(fv),
      });
    }
    return data;
  }, [monthlyInvestment, durationYears, expectedReturn]);

  const latestStats = chartData[chartData.length - 1] || { investedAmount: 0, projectedCorpus: 0 };
  const totalInvested = latestStats.investedAmount;
  const futureValue = latestStats.projectedCorpus;
  const wealthGain = Math.max(0, futureValue - totalInvested);

  return (
    <div className="space-y-6">
      {/* 1. Goal Input & Sliders */}
      <div className="bg-white rounded-lg border border-[#E1E8F0] p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-[#E1E8F0] pb-3">
          <div className="flex items-center space-x-2">
            <Target className="w-4 h-4 text-[#002E6E]" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
              SIP Investment Goal & Customizer
            </h3>
          </div>
          <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-50 border border-amber-200 text-amber-800">
            Sample
          </span>
        </div>

        {/* Goal Selector */}
        <div className="space-y-1.5">
          <label className="text-xs text-[#6B7C93] block">Target Financial Goal</label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {["Wealth Creation", "Home Downpayment", "Child Education", "Retirement"].map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setGoal(g)}
                className={`py-2 px-2.5 rounded-lg border text-xs font-medium text-center transition-colors ${
                  goal === g
                    ? "bg-[#002E6E] text-white border-[#002E6E]"
                    : "bg-[#F5F7FA] text-[#1B2A41] border-[#E1E8F0] hover:bg-white"
                }`}
              >
                {g}
              </button>
            ))}
          </div>
        </div>

        {/* Monthly Investment Slider */}
        <div className="space-y-1.5 pt-2">
          <div className="flex justify-between text-xs">
            <span className="text-[#6B7C93]">Monthly SIP Amount</span>
            <span className="font-bold tabular-nums font-mono text-[#002E6E]">
              ₹ {monthlyInvestment.toLocaleString("en-IN")} / month
            </span>
          </div>
          <input
            type="range"
            min={500}
            max={50000}
            step={500}
            value={monthlyInvestment}
            onChange={(e) => setMonthlyInvestment(Number(e.target.value))}
            className="w-full h-1.5 bg-[#E1E8F0] rounded-lg appearance-none cursor-pointer accent-[#002E6E]"
          />
          <div className="flex justify-between text-[10px] text-[#6B7C93] font-mono">
            <span>₹ 500</span>
            <span>₹ 25,000</span>
            <span>₹ 50,000</span>
          </div>
        </div>

        {/* Duration Slider */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-[#6B7C93]">Investment Horizon</span>
            <span className="font-bold tabular-nums font-mono text-[#002E6E]">
              {durationYears} Years ({durationYears * 12} Installments)
            </span>
          </div>
          <input
            type="range"
            min={1}
            max={25}
            step={1}
            value={durationYears}
            onChange={(e) => setDurationYears(Number(e.target.value))}
            className="w-full h-1.5 bg-[#E1E8F0] rounded-lg appearance-none cursor-pointer accent-[#002E6E]"
          />
          <div className="flex justify-between text-[10px] text-[#6B7C93] font-mono">
            <span>1 Yr</span>
            <span>10 Yrs</span>
            <span>20 Yrs</span>
            <span>25 Yrs</span>
          </div>
        </div>

        {/* Return Rate Slider */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-[#6B7C93]">Expected Annual Return</span>
            <span className="font-bold tabular-nums font-mono text-[#002E6E]">
              {expectedReturn}% p.a.
            </span>
          </div>
          <input
            type="range"
            min={6}
            max={18}
            step={0.5}
            value={expectedReturn}
            onChange={(e) => setExpectedReturn(Number(e.target.value))}
            className="w-full h-1.5 bg-[#E1E8F0] rounded-lg appearance-none cursor-pointer accent-[#002E6E]"
          />
          <div className="flex justify-between text-[10px] text-[#6B7C93] font-mono">
            <span>6%</span>
            <span>12% (Standard Equity)</span>
            <span>18%</span>
          </div>
        </div>
      </div>

      {/* 2. Customer Surplus Check (From Mock History) */}
      <div className="bg-white rounded-lg border border-[#E1E8F0] p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <PieChart className="w-4 h-4 text-[#002E6E]" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
              Monthly Cashflow Surplus Check
            </h3>
          </div>
          <span
            className={`text-[11px] font-bold px-2 py-0.5 rounded border ${
              isSurplusSafe
                ? "bg-green-50 border-green-200 text-green-700"
                : "bg-red-50 border-red-200 text-red-700"
            }`}
          >
            {isSurplusSafe ? "Comfortable Surplus" : "Exceeds Surplus"}
          </span>
        </div>

        <p className="text-xs text-[#6B7C93] leading-relaxed">
          Based on verified account cashflows (Income: ₹ {mockMonthlyIncome.toLocaleString("en-IN")}, Fixed Outflows: ₹ {mockExistingExpenses.toLocaleString("en-IN")}), your available discretionary surplus is <strong>₹ {monthlySurplus.toLocaleString("en-IN")}/mo</strong>.
        </p>

        <div className="p-3 bg-[#F5F7FA] rounded-lg border border-[#E1E8F0] flex items-center justify-between text-xs">
          <span>Surplus Allocation:</span>
          <span className="font-bold font-mono text-[#002E6E]">
            {surplusUtilizationPct}% utilized (₹ {monthlyInvestment.toLocaleString("en-IN")} of ₹ {monthlySurplus.toLocaleString("en-IN")})
          </span>
        </div>
      </div>

      {/* 3. Invested vs Illustrative Value Chart (Navy & Blue Only) */}
      <div className="bg-white rounded-lg border border-[#E1E8F0] p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-[#E1E8F0] pb-3">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
              Wealth Compounding Projection
            </h3>
            <span className="text-[11px] text-[#6B7C93]">Invested vs Illustrative Future Corpus</span>
          </div>
          <div className="flex items-center space-x-3 text-xs">
            <div className="flex items-center space-x-1.5">
              <div className="w-3 h-3 rounded bg-[#002E6E]" />
              <span className="text-[#6B7C93]">Invested</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <div className="w-3 h-3 rounded bg-[#00BAF2]" />
              <span className="text-[#6B7C93]">Illustrative Corpus</span>
            </div>
          </div>
        </div>

        {/* Recharts Bar Chart */}
        <div className="w-full h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <XAxis dataKey="year" stroke="#6B7C93" fontSize={11} tickLine={false} />
              <YAxis
                stroke="#6B7C93"
                fontSize={11}
                tickLine={false}
                tickFormatter={(val) => `₹${Math.round(val / 1000)}k`}
              />
              <Tooltip
                formatter={(value: any) => [`₹ ${Number(value).toLocaleString("en-IN")}`, ""]}
                contentStyle={{
                  backgroundColor: "#FFFFFF",
                  border: "1px solid #E1E8F0",
                  borderRadius: "8px",
                  fontSize: "12px",
                  fontFamily: "Inter, sans-serif",
                }}
              />
              <Bar dataKey="investedAmount" name="Invested Amount" fill="#002E6E" radius={[4, 4, 0, 0]} />
              <Bar dataKey="projectedCorpus" name="Projected Corpus" fill="#00BAF2" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Summary Metrics */}
        <div className="grid grid-cols-3 gap-3 pt-3 border-t border-[#E1E8F0] text-center">
          <div className="bg-[#F5F7FA] p-2.5 rounded-lg border border-[#E1E8F0]">
            <span className="text-[10px] text-[#6B7C93] block uppercase font-medium">Total Invested</span>
            <span className="text-sm font-bold text-[#1B2A41] tabular-nums font-mono">
              ₹ {totalInvested.toLocaleString("en-IN")}
            </span>
          </div>
          <div className="bg-[#F5F7FA] p-2.5 rounded-lg border border-[#E1E8F0]">
            <span className="text-[10px] text-[#6B7C93] block uppercase font-medium">Est. Wealth Gain</span>
            <span className="text-sm font-bold text-green-700 tabular-nums font-mono">
              + ₹ {wealthGain.toLocaleString("en-IN")}
            </span>
          </div>
          <div className="bg-[#F5F7FA] p-2.5 rounded-lg border border-[#E1E8F0]">
            <span className="text-[10px] text-[#6B7C93] block uppercase font-medium">Projected Corpus</span>
            <span className="text-sm font-bold text-[#002E6E] tabular-nums font-mono">
              ₹ {futureValue.toLocaleString("en-IN")}
            </span>
          </div>
        </div>
      </div>

      {/* 4. Fixed Non-Removable Disclaimer */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 space-y-1.5">
        <div className="flex items-center space-x-2 text-amber-900 font-semibold text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>Statutory Sample Disclaimer</span>
        </div>
        <p className="text-[11px] text-amber-800 leading-relaxed">
          Sample projection for illustrative purposes only. Mutual fund investments are subject to market risks; read all scheme related documents carefully. Past performance is no guarantee of future returns.
        </p>
      </div>
    </div>
  );
};

