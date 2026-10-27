/**
 * 청년 창업 체크리스트 & 공공데이터 비전 대시보드
 * static/js/app.js
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. DOM 요소 캐싱
    const form = document.getElementById("analyzeForm");
    const industryInput = document.getElementById("industryInput");
    const regionInput = document.getElementById("regionInput");
    const submitBtn = document.getElementById("submitBtn");
    const errorAlert = document.getElementById("errorAlert");
    const loadingSection = document.getElementById("loadingSection");
    const resultSection = document.getElementById("resultSection");
    const reportContainer = document.getElementById("reportContainer");
    const macroInfoBox = document.getElementById("macroInfoBox");
    const macroContent = document.getElementById("macroContent");
    const resultTitle = document.getElementById("resultTitle");
    const resultSubtitle = document.getElementById("resultSubtitle");
    const copyBtn = document.getElementById("copyBtn");
    const downloadBtn = document.getElementById("downloadBtn");

    // KPI 카드 요소
    const kpiNationalCurrent = document.getElementById("kpiNationalCurrent");
    const kpiNationalYoy = document.getElementById("kpiNationalYoy");
    const kpiRegionCurrent = document.getElementById("kpiRegionCurrent");
    const kpiRegionYoy = document.getElementById("kpiRegionYoy");
    const kpiTotalCost = document.getElementById("kpiTotalCost");
    const kpiCostDeposit = document.getElementById("kpiCostDeposit");
    const kpiSaturationLevel = document.getElementById("kpiSaturationLevel");
    const kpiSaturationScore = document.getElementById("kpiSaturationScore");

    // 테이블 요소
    const ntsTableBody = document.getElementById("ntsTableBody");
    const costTableBody = document.getElementById("costTableBody");

    // 세부 특화 프로파일 요소
    const microProfileBox = document.getElementById("microProfileBox");
    const microSubCategory = document.getElementById("microSubCategory");
    const microCostModel = document.getElementById("microCostModel");
    const microDailyBep = document.getElementById("microDailyBep");
    const microKeyFacilities = document.getElementById("microKeyFacilities");

    // 차트 인스턴스 저장용 객체 (재렌더링 시 기존 차트 삭제)
    let charts = {
        costDoughnut: null,
        lifecycleBar: null,
        regionalCostBar: null,
        locationPie: null
    };

    // 추가 Q&A 관련 요소
    const followupForm = document.getElementById("followupForm");
    const followupInput = document.getElementById("followupInput");
    const followupBtn = document.getElementById("followupBtn");
    const qaContainer = document.getElementById("qaContainer");
    const quickBtns = document.querySelectorAll(".quick-btn");

    let currentRawMarkdown = "";
    let currentIndustry = "";
    let currentRegion = "";

    // 2. 에러 알림 함수
    function showError(message) {
        errorAlert.textContent = message;
        errorAlert.style.display = "flex";
        errorAlert.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    function clearError() {
        errorAlert.textContent = "";
        errorAlert.style.display = "none";
    }

    // 4. 로딩 상태 토글
    function setLoading(isLoading) {
        if (isLoading) {
            clearError();
            resultSection.style.display = "none";
            loadingSection.style.display = "block";
            submitBtn.disabled = true;
            submitBtn.querySelector(".btn-text").textContent = "⏳ 공공데이터 및 Gemini AI 정밀 분석 중...";
            loadingSection.scrollIntoView({ behavior: "smooth", block: "start" });
        } else {
            loadingSection.style.display = "none";
            submitBtn.disabled = false;
            submitBtn.querySelector(".btn-text").textContent = "🚀 공공데이터 분석 및 AI 비전 리포트 생성";
        }
    }

    // 5. KPI 카드 갱신
    function updateKpiCards(stats) {
        const nts = stats.nts || {};
        const costs = stats.costs?.breakdown || {};

        kpiNationalCurrent.textContent = `${(nts.national_current || 0).toLocaleString()} 개소`;
        kpiNationalYoy.textContent = `전년대비 ${nts.national_yoy >= 0 ? '+' : ''}${nts.national_yoy}% (전월대비 ${nts.national_mom >= 0 ? '+' : ''}${nts.national_mom}%)`;

        kpiRegionCurrent.textContent = `${(nts.region_current || 0).toLocaleString()} 개소`;
        kpiRegionYoy.textContent = `${nts.region_name || '전국'} 기준 (전년동월 ${nts.region_yoy >= 0 ? '+' : ''}${nts.region_yoy}%)`;

        const totalCostVal = costs.total || 9500;
        kpiTotalCost.textContent = `${totalCostVal.toLocaleString()} 만 원`;
        kpiCostDeposit.textContent = `보증금 ${(costs.deposit || 0).toLocaleString()}만 · 시설비 ${(costs.facility || 0).toLocaleString()}만`;

        kpiSaturationLevel.textContent = nts.saturation_level ? nts.saturation_level.split(" ")[0] : "레드오션";
        kpiSaturationLevel.style.color = nts.saturation_color || "#ef4444";
        kpiSaturationScore.textContent = `포화도 위험 지수 ${nts.saturation_score || 85} / 100`;
    }

    // 6. 통계 데이터 테이블 렌더링
    function updateTables(stats) {
        const nts = stats.nts || {};
        const costs = stats.costs?.breakdown || {};

        // 국세청 테이블
        ntsTableBody.innerHTML = `
            <tr>
                <td><strong>전국 총계 (${nts.industry})</strong></td>
                <td><strong>${(nts.national_current || 0).toLocaleString()} 개소</strong></td>
                <td style="color: ${nts.national_yoy >= 0 ? '#10b981' : '#ef4444'}; font-weight: 700;">
                    ${nts.national_yoy >= 0 ? '+' : ''}${nts.national_yoy}%
                </td>
                <td style="color: ${nts.national_mom >= 0 ? '#10b981' : '#ef4444'}; font-weight: 700;">
                    ${nts.national_mom >= 0 ? '+' : ''}${nts.national_mom}%
                </td>
                <td><span class="badge-red">${nts.saturation_level || '성숙기 포화'}</span></td>
            </tr>
            <tr>
                <td><strong>목표 권역 (${nts.region_name})</strong></td>
                <td><strong>${(nts.region_current || 0).toLocaleString()} 개소</strong></td>
                <td style="color: ${nts.region_yoy >= 0 ? '#10b981' : '#ef4444'}; font-weight: 700;">
                    ${nts.region_yoy >= 0 ? '+' : ''}${nts.region_yoy}%
                </td>
                <td>-</td>
                <td><span class="badge-green">권역 상권 실측</span></td>
            </tr>
        `;

        // 창업비용 명세서 테이블
        const totalCost = costs.total || 1;
        const items = [
            { name: "임차 보증금", val: costs.deposit || 0, guide: "상가임대차보호법 확정일자 필수, 계약 종료 시 회수 가능 자산" },
            { name: "인테리어 및 설비비", val: costs.facility || 0, guide: "평당 150~250만 원 선, 원상복구 범위 계약서 사전 명시 필요" },
            { name: "초기 원자재 및 초도물품", val: costs.raw_materials || 0, guide: "첫 달 과다 발주 방지, 린(Lean) 방식으로 최소 재고 유지" },
            { name: "바닥 권리금 (영업권)", val: costs.premium || 0, guide: "유동인구 및 직전 3개년 매출 장부 반드시 사전 실사" },
            { name: "가맹비 / 교육비 / 브랜드", val: costs.franchise || 0, guide: "프랜차이즈 가맹 시 필수 지출, 개인 창업 시 0원 절감 가능" },
            { name: "기타 인허가 및 예비비", val: costs.others || 0, guide: "영업신고증 수수료, 화재보험, POS 단말기 및 비상 운영자금" }
        ];

        costTableBody.innerHTML = items.map(item => {
            const pct = ((item.val / totalCost) * 100).toFixed(1);
            return `
                <tr>
                    <td><strong>${item.name}</strong></td>
                    <td>${item.val.toLocaleString()} 만 원</td>
                    <td><strong style="color: #2563eb;">${pct}%</strong></td>
                    <td><small style="color: #475569;">${item.guide}</small></td>
                </tr>
            `;
        }).join("") + `
            <tr style="background-color: #f8fafc; font-weight: 800;">
                <td>합계 (총 창업비용)</td>
                <td style="color: #2563eb;">${totalCost.toLocaleString()} 만 원</td>
                <td>100.0%</td>
                <td><strong style="color: #0f172a;">정부 정책자금(청년전용창업융자) 최대 1억 한도 연계 검토 추천</strong></td>
            </tr>
        `;
    }

    // 7. Chart.js 시각화 차트 4종 렌더링
    function renderCharts(stats) {
        // 기존 차트 제거
        Object.keys(charts).forEach(key => {
            if (charts[key]) {
                charts[key].destroy();
                charts[key] = null;
            }
        });

        const costs = stats.costs?.breakdown || {};
        const regional = stats.costs?.regional_comparison || [];
        const lifecycle = stats.lifecycle || [];
        const locations = stats.locations || [];

        // 차트 1: 초기 창업비용 도넛 차트
        const ctxCost = document.getElementById("costDoughnutChart").getContext("2d");
        charts.costDoughnut = new Chart(ctxCost, {
            type: "doughnut",
            data: {
                labels: ["보증금", "설비·인테리어", "원자재비", "권리금", "가맹비", "기타"],
                datasets: [{
                    data: [
                        costs.deposit || 0,
                        costs.facility || 0,
                        costs.raw_materials || 0,
                        costs.premium || 0,
                        costs.franchise || 0,
                        costs.others || 0
                    ],
                    backgroundColor: [
                        "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#64748b"
                    ],
                    borderWidth: 2,
                    borderColor: "#ffffff"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right", labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${context.label}: ${context.parsed.toLocaleString()}만 원`;
                            }
                        }
                    }
                }
            }
        });

        // 차트 2: 1~7년차 매출액 및 생존 곡선 바/라인 혼합 차트
        const ctxLifecycle = document.getElementById("lifecycleBarChart").getContext("2d");
        charts.lifecycleBar = new Chart(ctxLifecycle, {
            type: "bar",
            data: {
                labels: lifecycle.map(l => l.year),
                datasets: [{
                    label: "기업 전체 수명 중 매출 기여도 (%)",
                    data: lifecycle.map(l => l.share),
                    backgroundColor: lifecycle.map((l, i) => i === 0 ? "#ef4444" : (i === 2 ? "#10b981" : "#3b82f6")),
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: value => value + "%" }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                const idx = context.dataIndex;
                                return lifecycle[idx]?.growth_stage ? `단계: ${lifecycle[idx].growth_stage}` : "";
                            }
                        }
                    }
                }
            }
        });

        // 차트 3: 권역별 창업비용 비교 수평 바 차트
        const ctxRegional = document.getElementById("regionalCostBarChart").getContext("2d");
        charts.regionalCostBar = new Chart(ctxRegional, {
            type: "bar",
            indexAxis: "y",
            data: {
                labels: regional.map(r => r.region),
                datasets: [{
                    label: "평균 총 창업비용 (만 원)",
                    data: regional.map(r => r.cost),
                    backgroundColor: ["#2563eb", "#3b82f6", "#60a5fa", "#93c5fd"],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` 평균 비용: ${context.parsed.x.toLocaleString()}만 원`;
                            }
                        }
                    }
                }
            }
        });

        // 차트 4: 선배 창업자 사업장 입지 분포 파이 차트
        const ctxLocation = document.getElementById("locationPieChart").getContext("2d");
        charts.locationPie = new Chart(ctxLocation, {
            type: "pie",
            data: {
                labels: locations.map(l => l.type.split(" ")[0]),
                datasets: [{
                    data: locations.map(l => l.ratio),
                    backgroundColor: ["#0284c7", "#0d9488", "#ea580c", "#e11d48", "#64748b"],
                    borderWidth: 2,
                    borderColor: "#ffffff"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right", labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${context.label}: ${context.parsed}%`;
                            }
                        }
                    }
                }
            }
        });
    }

    // 8. 폼 제출 이벤트 핸들러
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        clearError();

        const industry = industryInput.value.trim();
        const targetRegion = regionInput.value.trim();
        const mode = "pro"; // 전문가용 심층 리포트로 단일화

        if (!industry) {
            showError("⚠️ 창업 희망 업종을 입력해주세요. (예: 감성 디저트 카페, 24시 무인 편의점 등)");
            industryInput.focus();
            return;
        }

        currentIndustry = industry;
        setLoading(true);

        try {
            const response = await fetch("/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    industry: industry,
                    target_region: targetRegion,
                    mode: mode
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                const errorMsg = data.error || "분석 리포트를 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
                showError(`❌ 오류: ${errorMsg}`);
                setLoading(false);
                return;
            }

            // 분석 성공 처리
            currentRawMarkdown = data.report_markdown;
            currentIndustry = data.industry;
            currentRegion = data.target_region;

            // 기존 추가 Q&A 내역 초기화
            if (qaContainer) {
                qaContainer.innerHTML = "";
                qaContainer.style.display = "none";
            }

            resultTitle.textContent = `[${data.industry}] 데이터 기반 창업 진단 & 비전 리포트`;
            resultSubtitle.textContent = `국세청 100대 업종 매칭: [${data.stats?.matched_industry || data.industry}] · 목표 권역: [${data.stats?.matched_region || '전국'}]`;

            // 거시경제 및 고용 지표 (data 폴더 원천 실측 데이터)
            if (data.macro_info) {
                macroContent.textContent = data.macro_info.summary_text || `국내 물가상승률 ${data.macro_info.inflation_rate}, 성장률 ${data.macro_info.gdp_growth} (한국무역보험공사.csv) · 전국 폐업 소멸률 ${data.macro_info.closure_rate || '87.9%'} (근로복지공단.csv) · 자영업 평균소득 ${data.macro_info.self_employed_income || '163만 원'} (국민연금공단.csv)`;
                macroInfoBox.style.display = "block";
            } else {
                macroInfoBox.style.display = "none";
            }

            // 1. KPI 카드 및 세부 특화 프로파일 업데이트
            if (data.stats) {
                updateKpiCards(data.stats);
                updateTables(data.stats);
                renderCharts(data.stats);

                if (data.stats.micro_profile && microProfileBox) {
                    const mp = data.stats.micro_profile;
                    microSubCategory.textContent = mp.sub_category || data.industry;
                    microCostModel.textContent = mp.cost_model || "-";
                    microDailyBep.textContent = mp.daily_bep || "-";
                    microKeyFacilities.textContent = mp.key_facilities || "-";
                    microProfileBox.style.display = "block";
                } else if (microProfileBox) {
                    microProfileBox.style.display = "none";
                }
            }

            // 2. 마크다운 리포트 렌더링
            if (typeof marked !== "undefined") {
                reportContainer.innerHTML = marked.parse(currentRawMarkdown);
            } else {
                reportContainer.textContent = currentRawMarkdown;
            }

            setLoading(false);
            resultSection.style.display = "block";
            resultSection.scrollIntoView({ behavior: "smooth", block: "start" });

        } catch (err) {
            console.error("API 요청 실패:", err);
            showError("⚠️ 서버와의 통신에 실패했습니다. Flask 서버가 켜져 있는지 확인해주세요.");
            setLoading(false);
        }
    });

    // 9. 결과 복사 버튼
    copyBtn.addEventListener("click", async () => {
        if (!currentRawMarkdown) {
            alert("복사할 리포트 내용이 없습니다.");
            return;
        }

        try {
            await navigator.clipboard.writeText(currentRawMarkdown);
            const originalText = copyBtn.innerHTML;
            copyBtn.innerHTML = "✅ 복사 완료!";
            copyBtn.style.backgroundColor = "#dcfce7";
            copyBtn.style.color = "#166534";

            setTimeout(() => {
                copyBtn.innerHTML = originalText;
                copyBtn.style.backgroundColor = "";
                copyBtn.style.color = "";
            }, 2000);
        } catch (err) {
            const tempTextArea = document.createElement("textarea");
            tempTextArea.value = currentRawMarkdown;
            document.body.appendChild(tempTextArea);
            tempTextArea.select();
            document.execCommand("copy");
            document.body.removeChild(tempTextArea);
            alert("리포트 마크다운이 클립보드에 복사되었습니다.");
        }
    });

    // 10. Markdown 파일 다운로드 버튼
    downloadBtn.addEventListener("click", () => {
        if (!currentRawMarkdown) {
            alert("다운로드할 리포트 내용이 없습니다.");
            return;
        }

        const safeIndustryName = (currentIndustry || "창업").replace(/[^a-zA-Z0-9가-힣_-]/g, "_");
        const filename = `${safeIndustryName}_창업진단_비전리포트.md`;

        const blob = new Blob([currentRawMarkdown], { type: "text/markdown;charset=utf-8;" });
        const link = document.createElement("a");
        const url = URL.createObjectURL(blob);

        link.setAttribute("href", url);
        link.setAttribute("download", filename);
        link.style.visibility = "hidden";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    });

    // 11. 추천 빠른 질문 버튼 클릭 이벤트
    if (quickBtns) {
        quickBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                const questionText = btn.getAttribute("data-q");
                if (questionText && followupInput) {
                    followupInput.value = questionText;
                    followupInput.focus();
                }
            });
        });
    }

    // 12. 추가 질문(Q&A) 폼 제출 이벤트
    if (followupForm) {
        followupForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const question = followupInput.value.trim();

            if (!question) {
                alert("질문 내용을 입력해주세요.");
                followupInput.focus();
                return;
            }

            // 버튼 로딩 상태
            followupBtn.disabled = true;
            const originalBtnText = followupBtn.querySelector(".qa-btn-text").textContent;
            followupBtn.querySelector(".qa-btn-text").textContent = "답변 생성 중...";

            try {
                const response = await fetch("/ask", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        question: question,
                        industry: currentIndustry || "창업 일반",
                        target_region: currentRegion || "전국"
                    })
                });

                const data = await response.json();

                if (!response.ok || !data.success) {
                    alert(data.error || "답변을 생성하는 중 오류가 발생했습니다.");
                    return;
                }

                // 답변 카드 생성 및 추가
                const qaItem = document.createElement("div");
                qaItem.className = "qa-item";

                const parsedAnswer = typeof marked !== "undefined" 
                    ? marked.parse(data.answer_markdown) 
                    : data.answer_markdown;

                qaItem.innerHTML = `
                    <div class="qa-user-bubble">
                        <span class="qa-user-tag">Q. 추가 질문</span>
                        <span class="qa-user-text">${escapeHtml(data.question)}</span>
                    </div>
                    <div class="qa-ai-response markdown-body">
                        ${parsedAnswer}
                    </div>
                `;

                qaContainer.style.display = "flex";
                qaContainer.appendChild(qaItem);

                // 부드럽게 스크롤
                qaItem.scrollIntoView({ behavior: "smooth", block: "start" });
                followupInput.value = "";

            } catch (err) {
                console.error("추가 질의 실패:", err);
                alert("서버와의 통신에 실패했습니다.");
            } finally {
                followupBtn.disabled = false;
                followupBtn.querySelector(".qa-btn-text").textContent = originalBtnText;
            }
        });
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
});
