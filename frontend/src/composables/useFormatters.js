export const formatMoney = (v) =>
  (v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export const categoryMap = {
  cash: '现金/活期',
  investment: '股票',
  insurance: '保险',
  future_cash: '公积金/社保',
}

export const categoryLabel = (cat) => categoryMap[cat] || cat
