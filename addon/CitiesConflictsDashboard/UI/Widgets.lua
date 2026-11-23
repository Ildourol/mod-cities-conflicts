local ADDON_NAME, LifeDashboard = ...
LifeDashboard = LifeDashboard or {}
_G["CitiesConflictsDashboard"] = LifeDashboard
_G["PlayerbotsLifeDashboard"] = LifeDashboard

local Widgets = {}
LifeDashboard.Widgets = Widgets

-- Standard dark backdrop for 3.3.5
function Widgets:ApplyDarkBackdrop(frame, bgAlpha, edgeAlpha)
    bgAlpha = bgAlpha or 0.85
    edgeAlpha = edgeAlpha or 0.6
    frame:SetBackdrop({
        bgFile = "Interface\\ChatFrame\\ChatFrameBackground",
        edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
        tile = true, tileSize = 16, edgeSize = 14,
        insets = { left = 3, right = 3, top = 3, bottom = 3 }
    })
    frame:SetBackdropColor(0.08, 0.08, 0.12, bgAlpha)
    frame:SetBackdropBorderColor(0.3, 0.3, 0.45, edgeAlpha)
end

function Widgets:ApplyCardBackdrop(frame)
    frame:SetBackdrop({
        bgFile = "Interface\\ChatFrame\\ChatFrameBackground",
        edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
        tile = true, tileSize = 12, edgeSize = 10,
        insets = { left = 2, right = 2, top = 2, bottom = 2 }
    })
    frame:SetBackdropColor(0.12, 0.14, 0.18, 0.8)
    frame:SetBackdropBorderColor(0.4, 0.45, 0.6, 0.5)
end

-- â”€â”€â”€ Stat Card Creator â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function Widgets:CreateStatCard(parent, width, height, titleText)
    local card = CreateFrame("Frame", nil, parent)
    card:SetWidth(width)
    card:SetHeight(height)
    self:ApplyCardBackdrop(card)

    local title = card:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    title:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -6)
    title:SetText(titleText)
    title:SetTextColor(0.8, 0.8, 0.9)
    card.Title = title

    local value = card:CreateFontString(nil, "OVERLAY", "GameFontHighlightLarge")
    value:SetPoint("CENTER", card, "CENTER", 0, -4)
    value:SetText("0")
    value:SetTextColor(1, 0.82, 0)
    card.Value = value

    local subtext = card:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
    subtext:SetPoint("BOTTOMLEFT", card, "BOTTOMLEFT", 8, 5)
    subtext:SetText("")
    card.Subtext = subtext

    return card
end

-- â”€â”€â”€ Virtualized Table Frame (HybridScrollFrame Pattern) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function Widgets:CreateVirtualizedTable(parent, width, height, rowHeight, columns, onBindRow)
    local container = CreateFrame("Frame", nil, parent)
    container:SetWidth(width)
    container:SetHeight(height)
    container:EnableMouse(true)
    self:ApplyDarkBackdrop(container, 0.4, 0.3)

    -- Header row
    local headerBar = CreateFrame("Frame", nil, container)
    headerBar:SetWidth(width - 24)
    headerBar:SetHeight(22)
    headerBar:SetPoint("TOPLEFT", container, "TOPLEFT", 4, -4)

    local curX = 0
    headerBar.columns = {}
    for i, col in ipairs(columns) do
        local btn = CreateFrame("Button", nil, headerBar)
        btn:SetWidth(col.width)
        btn:SetHeight(20)
        btn:SetPoint("LEFT", headerBar, "LEFT", curX, 0)
        local fs = btn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        fs:SetPoint("LEFT", btn, "LEFT", 4, 0)
        fs:SetText(col.name)
        btn.Text = fs
        headerBar.columns[i] = btn
        curX = curX + col.width
    end

    -- ScrollFrame container
    local scrollFrame = CreateFrame("Frame", nil, container)
    scrollFrame:SetPoint("TOPLEFT", container, "TOPLEFT", 4, -28)
    scrollFrame:SetPoint("BOTTOMRIGHT", container, "BOTTOMRIGHT", -22, 4)

    -- ScrollBar
    local scrollBar = CreateFrame("Slider", nil, container)
    scrollBar:SetOrientation("VERTICAL")
    scrollBar:SetThumbTexture("Interface\\Buttons\\UI-ScrollBar-Knob")
    scrollBar:EnableMouse(true)
    scrollBar:SetMinMaxValues(0, 0)
    scrollBar:SetValue(0)
    scrollBar:SetValueStep(1)
    scrollBar:SetWidth(16)
    container.ScrollBar = scrollBar

    local function CreateArrow(label, side, y)
        local button = CreateFrame("Button", nil, container, "UIPanelButtonTemplate")
        button:SetWidth(18)
        button:SetHeight(16)
        button:SetPoint(side, container, side, -3, y)
        button:SetText(label)
        return button
    end
    local up = CreateArrow("^", "TOPRIGHT", -24)
    local down = CreateArrow("v", "BOTTOMRIGHT", 5)
    scrollBar:SetPoint("TOP", up, "BOTTOM", 0, -2)
    scrollBar:SetPoint("BOTTOM", down, "TOP", 0, 2)
    container.ScrollUp = up
    container.ScrollDown = down

    -- Pool of visible rows
    local visibleRowCount = math.floor((height - 32) / rowHeight)
    local rows = {}
    for i = 1, visibleRowCount do
        local row = CreateFrame("Button", nil, scrollFrame)
        row:SetWidth(width - 24)
        row:SetHeight(rowHeight)
        row:SetPoint("TOPLEFT", scrollFrame, "TOPLEFT", 0, -((i - 1) * rowHeight))

        -- Highlight texture on mouse hover
        local hl = row:CreateTexture(nil, "HIGHLIGHT")
        hl:SetAllPoints(row)
        hl:SetTexture("Interface\\QuestFrame\\UI-QuestTitleHighlight")
        hl:SetAlpha(0.25)

        -- Cell font strings
        row.cells = {}
        local cellX = 0
        for cIdx, col in ipairs(columns) do
            local fs = row:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
            fs:SetWidth(col.width - 6)
            fs:SetHeight(rowHeight)
            fs:SetPoint("LEFT", row, "LEFT", cellX + 4, 0)
            fs:SetJustifyH(col.align or "LEFT")
            row.cells[cIdx] = fs
            cellX = cellX + col.width
        end

        rows[i] = row
    end
    container.Rows = rows
    container.RowHeight = rowHeight
    container.VisibleRowCount = visibleRowCount
    container.DataList = {}

    local maxOffset = 0
    local updatingRange = false
    local function UpdateDisplay()
        local data = container.DataList
        local offset = math.floor(scrollBar:GetValue() + 0.5)
        if offset > 0 then up:Enable() else up:Disable() end
        if offset < maxOffset then down:Enable() else down:Disable() end
        for i, row in ipairs(rows) do
            local item = data[offset + i]
            if item then
                row:Show()
                if onBindRow then onBindRow(row, item, offset + i) end
            else
                row:Hide()
            end
        end
    end

    local function MoveTo(offset)
        scrollBar:SetValue(math.max(0, math.min(maxOffset, offset)))
    end

    local function OnWheel(_, delta)
        MoveTo(scrollBar:GetValue() - delta * 3)
    end

    scrollBar:SetScript("OnValueChanged", function()
        if not updatingRange then UpdateDisplay() end
    end)
    up:SetScript("OnClick", function() MoveTo(scrollBar:GetValue() - 1) end)
    down:SetScript("OnClick", function() MoveTo(scrollBar:GetValue() + 1) end)
    for _, frame in ipairs({ container, scrollFrame, scrollBar, up, down }) do
        frame:EnableMouseWheel(true)
        frame:SetScript("OnMouseWheel", OnWheel)
    end
    for _, row in ipairs(rows) do
        row:EnableMouseWheel(true)
        row:SetScript("OnMouseWheel", OnWheel)
    end

    -- Wrath keyboard events are captured by the enabled frame. Limit that to
    -- the hovered, scrollable list and yield while an edit box has focus.
    local keyboardEnabled = false
    local function SetKeyboard(enabled)
        if keyboardEnabled ~= enabled then
            keyboardEnabled = enabled
            container:EnableKeyboard(enabled)
        end
    end
    container:SetScript("OnUpdate", function()
        local editing = Widgets.activeSearch or (GetCurrentKeyBoardFocus and GetCurrentKeyBoardFocus()) or
            (ChatEdit_GetActiveWindow and ChatEdit_GetActiveWindow())
        local hovered = maxOffset > 0 and not editing and MouseIsOver(container)
        if hovered and GetMouseFocus then
            local hit = GetMouseFocus()
            while hit and hit ~= container do hit = hit:GetParent() end
            hovered = hit == container
        end
        SetKeyboard(hovered and true or false)
    end)
    container:SetScript("OnHide", function() SetKeyboard(false) end)
    container:SetScript("OnKeyDown", function(_, key)
        local value = scrollBar:GetValue()
        if key == "UP" then MoveTo(value - 1)
        elseif key == "DOWN" then MoveTo(value + 1)
        elseif key == "PAGEUP" then MoveTo(value - visibleRowCount)
        elseif key == "PAGEDOWN" then MoveTo(value + visibleRowCount)
        elseif key == "HOME" then MoveTo(0)
        elseif key == "END" then MoveTo(maxOffset)
        elseif key == "ESCAPE" and LifeDashboard.HideWindow then LifeDashboard:HideWindow()
        end
    end)

    container.SetData = function(self, dataList)
        self.DataList = dataList or {}
        maxOffset = math.max(0, #self.DataList - visibleRowCount)
        local previous = scrollBar:GetValue()
        updatingRange = true
        scrollBar:SetMinMaxValues(0, maxOffset)
        MoveTo(previous)
        updatingRange = false
        UpdateDisplay()
    end

    container.Refresh = UpdateDisplay
    UpdateDisplay()

    return container
end

-- â”€â”€â”€ Search Box Creator â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function Widgets:CreateSearchBox(parent, width, placeholder, onTextChanged)
    local eb = CreateFrame("EditBox", nil, parent)
    eb:SetWidth(width)
    eb:SetHeight(22)
    eb:SetFontObject("GameFontHighlightSmall")
    eb:SetAutoFocus(false)
    eb:SetTextInsets(6, 6, 2, 2)
    self:ApplyDarkBackdrop(eb, 0.7, 0.5)

    local ph = eb:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
    ph:SetPoint("LEFT", eb, "LEFT", 6, 0)
    ph:SetText(placeholder or "Search...")

    eb:SetScript("OnTextChanged", function(self)
        local text = self:GetText()
        if text == "" then
            ph:Show()
        else
            ph:Hide()
        end
        if onTextChanged then
            onTextChanged(text)
        end
    end)

    eb:SetScript("OnEscapePressed", function(self)
        self:ClearFocus()
    end)
    eb:SetScript("OnEditFocusGained", function(self) Widgets.activeSearch = self end)
    eb:SetScript("OnEditFocusLost", function(self)
        if Widgets.activeSearch == self then Widgets.activeSearch = nil end
    end)

    return eb
end
