// Функция для поиска селектора Aspect Ratio
function findAspectRatioButton() {
	// Ищем div с классом mat-mdc-select-value, содержащий "Auto", "1:1", "9:16" и т.д.
	const selects = document.querySelectorAll('.mat-mdc-select-value')

	for (const select of selects) {
		const text = select.textContent.trim()
		// Проверяем, что это соотношение сторон
		if (text === 'Auto' || text.match(/^\d+:\d+$/)) {
			// Находим родительский элемент mat-select, который кликабелен
			const matSelect = select.closest('mat-select')
			if (matSelect) {
				return matSelect
			}
		}
	}

	return null
}

// Функция для поиска опций в выпадающем списке
function findAspectRatioOptions() {
	// Ищем mat-option элементы
	const options = document.querySelectorAll('mat-option')
	const aspectOptions = []

	for (const option of options) {
		const text = option.textContent.trim()
		// Проверяем, что это соотношение сторон
		if (text.match(/^\d+:\d+$/) || text === 'Auto') {
			aspectOptions.push({
				element: option,
				value: text,
			})
		}
	}

	return aspectOptions
}

// Функция для применения сохранённого значения
async function applySavedAspectRatio() {
	try {
		const result = await chrome.storage.local.get(['aspectRatio'])
		const savedRatio = result.aspectRatio

		if (!savedRatio) {
			console.log('[Nanobanana] Нет сохранённого значения')
			return
		}

		console.log('[Nanobanana] Применяю:', savedRatio)

		// Ждём появления кнопки
		await waitForElement(() => findAspectRatioButton(), 10000)

		const button = findAspectRatioButton()
		if (!button) {
			console.log('[Nanobanana] Кнопка не найдена')
			return
		}

		const currentValue = button.textContent.trim()
		console.log('[Nanobanana] Текущее значение:', currentValue)

		if (currentValue === savedRatio) {
			console.log('[Nanobanana] Уже установлено')
			return
		}

		// Открываем список
		button.click()
		await new Promise((resolve) => setTimeout(resolve, 500))

		const options = findAspectRatioOptions()
		console.log('[Nanobanana] Найдено опций:', options.length)

		const targetOption = options.find((opt) => opt.value === savedRatio)

		if (targetOption) {
			targetOption.element.click()
			console.log('[Nanobanana] ✓ Применено:', savedRatio)
		} else {
			console.log('[Nanobanana] Опция не найдена:', savedRatio)
		}
	} catch (error) {
		console.error('[Nanobanana] Ошибка:', error.message)
	}
}

// Функция для отслеживания изменений
function watchAspectRatioChanges() {
	// Отслеживаем клики по mat-option
	document.addEventListener(
		'click',
		async (e) => {
			const target = e.target.closest('mat-option')

			if (target) {
				const text = target.textContent.trim()
				if (text.match(/^\d+:\d+$/) || text === 'Auto') {
					await chrome.storage.local.set({ aspectRatio: text })
					console.log('[Nanobanana] Сохранено:', text)
				}
			}
		},
		true
	)
}

// Вспомогательная функция для ожидания элемента
function waitForElement(finder, timeout = 5000) {
	return new Promise((resolve, reject) => {
		const startTime = Date.now()

		const check = () => {
			const element = finder()
			if (element) {
				resolve(element)
			} else if (Date.now() - startTime > timeout) {
				reject(new Error('Timeout'))
			} else {
				setTimeout(check, 100)
			}
		}

		check()
	})
}

// Запуск при загрузке страницы
;(async function init() {
	console.log('[Nanobanana] Запущено на:', window.location.href)

	// Проверяем URL
	if (
		window.location.pathname.includes('/prompts/new_chat') ||
		window.location.pathname.includes('/app')
	) {
		await applySavedAspectRatio()
		watchAspectRatioChanges()
	}

	// Отслеживаем переходы по SPA
	let lastUrl = location.href
	new MutationObserver(async () => {
		const url = location.href
		if (url !== lastUrl) {
			lastUrl = url
			console.log('[Nanobanana] Переход на:', url)

			if (url.includes('/prompts/new_chat') || url.includes('/app')) {
				await new Promise((resolve) => setTimeout(resolve, 1000))
				await applySavedAspectRatio()
			}
		}
	}).observe(document, { subtree: true, childList: true })
})()
